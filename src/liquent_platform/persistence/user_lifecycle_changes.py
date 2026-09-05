"""Atomic authorized persistence of complete user lifecycle snapshots."""

from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy import Connection, Engine, Row, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.lifecycle import (
    AuthorizedUserLifecycleChange,
    UserLifecycleChangeId,
    UserLifecycleIntent,
    UserLifecycleRevisionId,
)
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_errors import (
    UserLifecycleChangeConflict,
    UserLifecycleChangeStoreUnavailable,
)

_SELECT_CHANGE = text(
    "SELECT * FROM user_lifecycle_changes WHERE change_id=:change"
)
_LOCK = text(
    "LOCK TABLE identity_users, user_lifecycle_management_authorities,"
    " user_lifecycle_revisions, user_lifecycle_revision_members,"
    " user_lifecycle_current_revision, user_lifecycle_changes,"
    " browser_sessions, identity_admissions, workspace_memberships,"
    " workspace_onboarding_management,"
    " workspace_membership_management_authorities,"
    " oidc_trust_management_authorities,"
    " workspace_lifecycle_management_authorities"
    " IN SHARE ROW EXCLUSIVE MODE"
)
_PERMITS = text(
    "SELECT 1 FROM identity_users AS actor"
    " JOIN user_lifecycle_management_authorities AS authority"
    " ON authority.user_id=actor.user_id"
    " WHERE actor.user_id=:actor AND actor.status='active'"
    " AND authority.status='active'"
)
_CURRENT = text(
    "SELECT revision_id FROM user_lifecycle_current_revision"
    " WHERE singleton_key=1"
)
_MEMBERS = text(
    "SELECT user_id,status FROM user_lifecycle_revision_members"
    " WHERE revision_id=:expected ORDER BY user_id"
)
_USERS = text("SELECT user_id,status FROM identity_users ORDER BY user_id")
_TARGET = text("SELECT status FROM identity_users WHERE user_id=:target")
_DRAINED = text(
    "SELECT NOT EXISTS (SELECT 1 FROM browser_sessions"
    " WHERE user_id=:target AND revoked_at IS NULL AND expires_at>:now)"
    " AND NOT EXISTS (SELECT 1 FROM identity_admissions"
    " WHERE target_user_id=:target AND consumed_at IS NULL AND expires_at>:now)"
    " AND NOT EXISTS (SELECT 1 FROM workspace_memberships"
    " WHERE user_id=:target AND status='active')"
    " AND NOT EXISTS (SELECT 1 FROM workspace_onboarding_management"
    " WHERE user_id=:target AND status='active')"
    " AND NOT EXISTS (SELECT 1 FROM workspace_membership_management_authorities"
    " WHERE user_id=:target AND status='active')"
    " AND NOT EXISTS (SELECT 1 FROM oidc_trust_management_authorities"
    " WHERE user_id=:target AND status='active')"
    " AND NOT EXISTS (SELECT 1 FROM user_lifecycle_management_authorities"
    " WHERE user_id=:target AND status='active')"
    " AND NOT EXISTS (SELECT 1 FROM workspace_lifecycle_management_authorities"
    " WHERE user_id=:target AND status='active')"
)
_INSERT_USER = text(
    "INSERT INTO identity_users (user_id,status) VALUES (:target,'active')"
)
_UPDATE_USER = text(
    "UPDATE identity_users SET status=:status WHERE user_id=:target"
)
_INSERT_REVISION = text(
    "INSERT INTO user_lifecycle_revisions (revision_id) VALUES (:revision)"
)
_INSERT_MEMBER = text(
    "INSERT INTO user_lifecycle_revision_members"
    " (revision_id,user_id,status) VALUES (:revision,:user,:status)"
)
_UPDATE_CURRENT = text(
    "UPDATE user_lifecycle_current_revision SET revision_id=:revision"
    " WHERE singleton_key=1 AND revision_id=:expected"
)
_INSERT_CHANGE = text(
    "INSERT INTO user_lifecycle_changes"
    " (change_id,actor_user_id,target_user_id,intent,expected_revision_id,"
    " resulting_revision_id)"
    " VALUES (:change,:actor,:target,:intent,:expected,:revision)"
)
_SELECT_REVISION = text(
    "SELECT 1 FROM user_lifecycle_revisions WHERE revision_id=:revision"
)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise UserLifecycleChangeStoreUnavailable
    return value.encode("utf-8")


def _stored(value: object) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)) or not value:
        raise UserLifecycleChangeStoreUnavailable
    return bytes(value)


def _decode(value: object) -> str:
    try:
        result = _stored(value).decode("utf-8")
    except UnicodeDecodeError:
        raise UserLifecycleChangeStoreUnavailable from None
    if not result:
        raise UserLifecycleChangeStoreUnavailable
    return result


def _aware(value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise UserLifecycleChangeStoreUnavailable
    if value.utcoffset() is None:
        raise UserLifecycleChangeStoreUnavailable
    return value


class DatabaseAuthorizedUserLifecycleChanges:
    """Order current authority, drain, complete revision, and retry decision."""

    __slots__ = ("_engine", "_generate_user_id", "_generate_revision_id", "_now")

    def __init__(
        self,
        engine: Engine,
        *,
        generate_user_id: Callable[[], UserId],
        generate_revision_id: Callable[[], UserLifecycleRevisionId],
        now: Callable[[], datetime],
    ) -> None:
        self._engine = engine
        self._generate_user_id = generate_user_id
        self._generate_revision_id = generate_revision_id
        self._now = now

    def __repr__(self) -> str:
        return "DatabaseAuthorizedUserLifecycleChanges()"

    def create_user(
        self,
        change_id: UserLifecycleChangeId,
        principal: SessionPrincipal,
        expected_revision: UserLifecycleRevisionId,
    ) -> AuthorizedUserLifecycleChange | None:
        return self._run(lambda: self._change(
            change_id, principal, None, UserLifecycleIntent.CREATE,
            expected_revision,
        ))

    def change_user_status(
        self,
        change_id: UserLifecycleChangeId,
        principal: SessionPrincipal,
        target_user_id: UserId,
        intent: UserLifecycleIntent,
        expected_revision: UserLifecycleRevisionId,
    ) -> AuthorizedUserLifecycleChange | None:
        if intent not in {
            UserLifecycleIntent.DEACTIVATE,
            UserLifecycleIntent.REACTIVATE,
        }:
            raise UserLifecycleChangeStoreUnavailable
        return self._run(lambda: self._change(
            change_id, principal, target_user_id, intent, expected_revision
        ))

    @staticmethod
    def _run(operation: Callable[[], Any]) -> Any:
        try:
            return operation()
        except UserLifecycleChangeConflict as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure: type[Exception] = UserLifecycleChangeConflict
        except UserLifecycleChangeStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure = UserLifecycleChangeStoreUnavailable
        except Exception:
            failure = UserLifecycleChangeStoreUnavailable
        raise failure()

    def _change(
        self,
        change_id: UserLifecycleChangeId,
        principal: SessionPrincipal,
        target_user_id: UserId | None,
        intent: UserLifecycleIntent,
        expected_revision: UserLifecycleRevisionId,
    ) -> AuthorizedUserLifecycleChange | None:
        if (
            type(change_id) is not UserLifecycleChangeId
            or type(principal) is not SessionPrincipal
            or type(intent) is not UserLifecycleIntent
            or type(expected_revision) is not UserLifecycleRevisionId
        ):
            raise UserLifecycleChangeStoreUnavailable
        parameters: dict[str, Any] = {
            "change": _encode(change_id.value),
            "actor": _encode(principal.user_id),
            "expected": _encode(expected_revision.value),
            "intent": intent.value,
        }
        if target_user_id is not None:
            parameters["target"] = _encode(target_user_id)
        with self._engine.begin() as transaction:
            if transaction.dialect.name not in {"postgresql", "sqlite"}:
                raise UserLifecycleChangeStoreUnavailable
            existing = transaction.execute(_SELECT_CHANGE, parameters).first()
            if existing is not None:
                return self._resolve(
                    transaction, existing, change_id, intent, parameters
                )
            if transaction.dialect.name == "postgresql":
                transaction.execute(_LOCK)
                existing = transaction.execute(_SELECT_CHANGE, parameters).first()
                if existing is not None:
                    return self._resolve(
                        transaction, existing, change_id, intent, parameters
                    )
            if transaction.execute(_PERMITS, parameters).first() is None:
                return None
            current = transaction.scalar(_CURRENT)
            if current is None or _stored(current) != parameters["expected"]:
                return None
            current_members = [
                (_stored(row.user_id), row.status)
                for row in transaction.execute(_MEMBERS, parameters)
            ]
            users = [
                (_stored(row.user_id), row.status)
                for row in transaction.execute(_USERS)
            ]
            if current_members != users:
                raise UserLifecycleChangeStoreUnavailable

            if intent is UserLifecycleIntent.CREATE:
                generated = self._generate_user_id()
                if type(generated) is not str or not generated:
                    raise UserLifecycleChangeStoreUnavailable
                parameters["target"] = _encode(generated)
                transaction.execute(_INSERT_USER, parameters)
                users.append((parameters["target"], "active"))
                users.sort()
            else:
                target = transaction.execute(_TARGET, parameters).first()
                required = (
                    "active"
                    if intent is UserLifecycleIntent.DEACTIVATE
                    else "inactive"
                )
                result = "inactive" if required == "active" else "active"
                if target is None or target.status != required:
                    return None
                if intent is UserLifecycleIntent.DEACTIVATE:
                    parameters["now"] = _aware(self._now())
                    if not transaction.scalar(_DRAINED, parameters):
                        return None
                transaction.execute(_UPDATE_USER, dict(parameters, status=result))
                users = [
                    (user, result if user == parameters["target"] else status)
                    for user, status in users
                ]

            revision_id = self._generate_revision_id()
            if type(revision_id) is not UserLifecycleRevisionId:
                raise UserLifecycleChangeStoreUnavailable
            revision = _encode(revision_id.value)
            transaction.execute(_INSERT_REVISION, {"revision": revision})
            for user, status in users:
                transaction.execute(
                    _INSERT_MEMBER,
                    {"revision": revision, "user": user, "status": status},
                )
            if transaction.execute(
                _UPDATE_CURRENT,
                {"revision": revision, "expected": parameters["expected"]},
            ).rowcount != 1:
                raise UserLifecycleChangeStoreUnavailable
            transaction.execute(_INSERT_CHANGE, dict(parameters, revision=revision))
            return AuthorizedUserLifecycleChange(
                change_id,
                revision_id,
                UserId(_decode(parameters["target"])),
                intent,
            )

    @staticmethod
    def _resolve(
        transaction: Connection,
        row: Row[Any],
        change_id: UserLifecycleChangeId,
        intent: UserLifecycleIntent,
        parameters: dict[str, Any],
    ) -> AuthorizedUserLifecycleChange:
        if (
            _stored(row.actor_user_id) != parameters["actor"]
            or row.intent != intent.value
            or _stored(row.expected_revision_id) != parameters["expected"]
            or (
                "target" in parameters
                and _stored(row.target_user_id) != parameters["target"]
            )
        ):
            raise UserLifecycleChangeConflict
        revision = _stored(row.resulting_revision_id)
        if transaction.execute(
            _SELECT_REVISION, {"revision": revision}
        ).first() is None:
            raise UserLifecycleChangeStoreUnavailable
        return AuthorizedUserLifecycleChange(
            change_id,
            UserLifecycleRevisionId(_decode(revision)),
            UserId(_decode(row.target_user_id)),
            intent,
        )
