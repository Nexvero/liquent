"""Atomic regular lifecycle changes for global OIDC-trust authority."""

from collections.abc import Callable
from typing import Any

from sqlalchemy import Connection, Engine, Row, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.oidc_trust import (
    AuthorizedOidcTrustAuthorityLifecycleChange,
    OidcTrustAuthorityLifecycleChangeId,
    OidcTrustAuthorityLifecycleIntent,
    OidcTrustAuthoritySetRevisionId,
)
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_errors import (
    OidcTrustAuthorityLifecycleConflict,
    OidcTrustAuthorityLifecycleUnavailable,
)

_LOCK = text(
    "LOCK TABLE identity_users, oidc_trust_management_authorities,"
    " oidc_trust_authority_set_revisions, oidc_trust_authority_set_members,"
    " oidc_trust_authority_current_set, oidc_trust_authority_lifecycle_changes"
    " IN SHARE ROW EXCLUSIVE MODE"
)
_SELECT_CHANGE = text(
    "SELECT * FROM oidc_trust_authority_lifecycle_changes WHERE change_id=:change"
)
_FOUNDATION = text(
    "SELECT 1 FROM identity_users AS actor"
    " JOIN oidc_trust_management_authorities AS authority"
    " ON authority.user_id=actor.user_id"
    " JOIN identity_users AS target ON target.user_id=:target"
    " WHERE actor.user_id=:actor AND actor.status='active'"
    " AND target.status='active' AND authority.status='active'"
)
_CURRENT = text(
    "SELECT revision_id FROM oidc_trust_authority_current_set"
    " WHERE singleton_key=1"
)
_INVENTORY = text(
    "SELECT authority.user_id,authority.status,users.status AS user_status"
    " FROM oidc_trust_management_authorities AS authority"
    " JOIN identity_users AS users ON users.user_id=authority.user_id"
    " ORDER BY authority.user_id"
)
_MEMBERS = text(
    "SELECT user_id,status FROM oidc_trust_authority_set_members"
    " WHERE revision_id=:expected ORDER BY user_id"
)
_INSERT_AUTHORITY = text(
    "INSERT INTO oidc_trust_management_authorities (user_id,status)"
    " VALUES (:target,'active')"
)
_UPDATE_AUTHORITY = text(
    "UPDATE oidc_trust_management_authorities SET status=:result_status"
    " WHERE user_id=:target AND status=:required_status"
)
_INSERT_REVISION = text(
    "INSERT INTO oidc_trust_authority_set_revisions (revision_id)"
    " VALUES (:revision)"
)
_INSERT_MEMBER = text(
    "INSERT INTO oidc_trust_authority_set_members"
    " (revision_id,user_id,status) VALUES (:revision,:user,:status)"
)
_UPDATE_CURRENT = text(
    "UPDATE oidc_trust_authority_current_set SET revision_id=:revision"
    " WHERE singleton_key=1 AND revision_id=:expected"
)
_INSERT_CHANGE = text(
    "INSERT INTO oidc_trust_authority_lifecycle_changes"
    " (change_id,actor_user_id,target_user_id,intent,expected_revision_id,"
    " resulting_revision_id)"
    " VALUES (:change,:actor,:target,:intent,:expected,:revision)"
)
_SELECT_REVISION = text(
    "SELECT revision_id FROM oidc_trust_authority_set_revisions"
    " WHERE revision_id=:revision"
)


def _fail() -> None:
    raise OidcTrustAuthorityLifecycleUnavailable


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        _fail()
    return value.encode("utf-8")


def _stored(value: object) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)) or not value:
        _fail()
    return bytes(value)


def _decode(value: object) -> str:
    try:
        decoded = _stored(value).decode("utf-8")
    except UnicodeDecodeError:
        raise OidcTrustAuthorityLifecycleUnavailable from None
    if not decoded:
        _fail()
    return decoded


class DatabaseAuthorizedOidcTrustAuthorityLifecycle:
    """Order authority, expected set, transition, snapshot, and retry."""

    __slots__ = ("_engine", "_generate_revision_id")

    def __init__(
        self,
        engine: Engine,
        *,
        generate_revision_id: Callable[[], OidcTrustAuthoritySetRevisionId],
    ) -> None:
        self._engine = engine
        self._generate_revision_id = generate_revision_id

    def __repr__(self) -> str:
        return "DatabaseAuthorizedOidcTrustAuthorityLifecycle()"

    def change_authority(
        self,
        change_id: OidcTrustAuthorityLifecycleChangeId,
        principal: SessionPrincipal,
        target_user_id: UserId,
        intent: OidcTrustAuthorityLifecycleIntent,
        expected_revision: OidcTrustAuthoritySetRevisionId,
    ) -> AuthorizedOidcTrustAuthorityLifecycleChange | None:
        try:
            return self._change(
                change_id, principal, target_user_id, intent, expected_revision
            )
        except OidcTrustAuthorityLifecycleConflict as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure: type[Exception] = OidcTrustAuthorityLifecycleConflict
        except OidcTrustAuthorityLifecycleUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure = OidcTrustAuthorityLifecycleUnavailable
        except Exception:
            failure = OidcTrustAuthorityLifecycleUnavailable
        raise failure()

    def _change(
        self,
        change_id: OidcTrustAuthorityLifecycleChangeId,
        principal: SessionPrincipal,
        target_user_id: UserId,
        intent: OidcTrustAuthorityLifecycleIntent,
        expected_revision: OidcTrustAuthoritySetRevisionId,
    ) -> AuthorizedOidcTrustAuthorityLifecycleChange | None:
        if (
            type(change_id) is not OidcTrustAuthorityLifecycleChangeId
            or type(principal) is not SessionPrincipal
            or type(intent) is not OidcTrustAuthorityLifecycleIntent
            or type(expected_revision) is not OidcTrustAuthoritySetRevisionId
        ):
            _fail()
        parameters = {
            "change": _encode(change_id.value),
            "actor": _encode(principal.user_id),
            "target": _encode(target_user_id),
            "intent": intent.value,
            "expected": _encode(expected_revision.value),
        }
        with self._engine.begin() as transaction:
            if transaction.dialect.name not in {"postgresql", "sqlite"}:
                _fail()
            existing = transaction.execute(_SELECT_CHANGE, parameters).first()
            if existing is not None:
                return self._resolve(transaction, existing, change_id, intent, parameters)
            if transaction.dialect.name == "postgresql":
                transaction.execute(_LOCK)
                existing = transaction.execute(_SELECT_CHANGE, parameters).first()
                if existing is not None:
                    return self._resolve(
                        transaction, existing, change_id, intent, parameters
                    )
            if transaction.execute(_FOUNDATION, parameters).first() is None:
                return None
            current = transaction.execute(_CURRENT).first()
            if current is None or _stored(current.revision_id) != parameters["expected"]:
                return None
            inventory = transaction.execute(_INVENTORY).all()
            members = transaction.execute(_MEMBERS, parameters).all()
            if self._snapshot(inventory) != self._snapshot(members):
                _fail()
            changed = self._transition(inventory, parameters["target"], intent)
            if changed is None:
                return None
            revision_id = self._generate_revision_id()
            if type(revision_id) is not OidcTrustAuthoritySetRevisionId:
                _fail()
            revision = _encode(revision_id.value)
            values = dict(parameters, revision=revision)
            if intent is OidcTrustAuthorityLifecycleIntent.GRANT:
                transaction.execute(_INSERT_AUTHORITY, values)
            else:
                result_status = (
                    "inactive"
                    if intent is OidcTrustAuthorityLifecycleIntent.DEACTIVATE
                    else "active"
                )
                required_status = "active" if result_status == "inactive" else "inactive"
                if transaction.execute(
                    _UPDATE_AUTHORITY,
                    dict(
                        values,
                        result_status=result_status,
                        required_status=required_status,
                    ),
                ).rowcount != 1:
                    _fail()
            transaction.execute(_INSERT_REVISION, values)
            for user, status in changed:
                transaction.execute(
                    _INSERT_MEMBER,
                    dict(values, user=user, status=status),
                )
            if transaction.execute(_UPDATE_CURRENT, values).rowcount != 1:
                _fail()
            transaction.execute(_INSERT_CHANGE, values)
            return AuthorizedOidcTrustAuthorityLifecycleChange(
                change_id, revision_id, target_user_id, intent
            )

    @staticmethod
    def _snapshot(rows: list[Row[Any]]) -> list[tuple[bytes, str]]:
        snapshot = []
        for row in rows:
            if row.status not in {"active", "inactive"}:
                _fail()
            snapshot.append((_stored(row.user_id), row.status))
        return snapshot

    @staticmethod
    def _transition(
        inventory: list[Row[Any]], target: bytes,
        intent: OidcTrustAuthorityLifecycleIntent,
    ) -> list[tuple[bytes, str]] | None:
        current = {user: (status, user_status) for user, status, user_status in (
            (_stored(row.user_id), row.status, row.user_status) for row in inventory
        )}
        target_state = current.get(target)
        if intent is OidcTrustAuthorityLifecycleIntent.GRANT:
            if target_state is not None:
                return None
            current[target] = ("active", "active")
        elif intent is OidcTrustAuthorityLifecycleIntent.DEACTIVATE:
            if target_state is None or target_state[0] != "active":
                return None
            current[target] = ("inactive", target_state[1])
            if not any(
                status == "active" and user_status == "active"
                for status, user_status in current.values()
            ):
                return None
        else:
            if target_state is None or target_state[0] != "inactive":
                return None
            current[target] = ("active", target_state[1])
        return [(user, state[0]) for user, state in sorted(current.items())]

    @staticmethod
    def _resolve(
        transaction: Connection,
        row: Row[Any],
        change_id: OidcTrustAuthorityLifecycleChangeId,
        intent: OidcTrustAuthorityLifecycleIntent,
        parameters: dict[str, bytes | str],
    ) -> AuthorizedOidcTrustAuthorityLifecycleChange:
        if (
            _stored(row.actor_user_id) != parameters["actor"]
            or _stored(row.target_user_id) != parameters["target"]
            or row.intent != intent.value
            or _stored(row.expected_revision_id) != parameters["expected"]
        ):
            raise OidcTrustAuthorityLifecycleConflict
        revision = _stored(row.resulting_revision_id)
        if transaction.execute(
            _SELECT_REVISION, {"revision": revision}
        ).first() is None:
            _fail()
        return AuthorizedOidcTrustAuthorityLifecycleChange(
            change_id,
            OidcTrustAuthoritySetRevisionId(_decode(revision)),
            UserId(_decode(parameters["target"])),
            intent,
        )
