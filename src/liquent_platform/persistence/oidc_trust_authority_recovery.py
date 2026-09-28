"""Offline recovery of historically authorized global OIDC-trust authority."""

from collections.abc import Callable
from typing import Any

from sqlalchemy import Connection, Engine, Row, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.oidc_trust import (
    OidcTrustAuthorityRecoveryId,
    OidcTrustAuthoritySetRevisionId,
    RecoveredOidcTrustAuthoritySet,
)
from liquent_platform.persistence.identity_errors import (
    OidcTrustAuthorityRecoveryConflict,
    OidcTrustAuthorityRecoveryUnavailable,
)

_LOCK = text(
    "LOCK TABLE identity_users, oidc_trust_management_authorities,"
    " oidc_trust_authority_set_revisions, oidc_trust_authority_set_members,"
    " oidc_trust_authority_current_set, oidc_trust_authority_lifecycle_changes,"
    " oidc_trust_authority_recoveries IN SHARE ROW EXCLUSIVE MODE"
)
_SELECT_RECOVERY = text(
    "SELECT * FROM oidc_trust_authority_recoveries WHERE recovery_id=:recovery"
)
_TARGET = text(
    "SELECT 1 FROM identity_users AS users"
    " JOIN oidc_trust_management_authorities AS authority"
    " ON authority.user_id=users.user_id"
    " WHERE users.user_id=:target AND users.status='active'"
    " AND authority.status='inactive'"
)
_CURRENT = text(
    "SELECT revision_id FROM oidc_trust_authority_current_set"
    " WHERE singleton_key=1"
)
_TERMINAL = text(
    "SELECT"
    " ((SELECT count(*) FROM oidc_trust_authority_lifecycle_changes"
    " WHERE resulting_revision_id=:expected) +"
    " (SELECT count(*) FROM oidc_trust_authority_recoveries"
    " WHERE resulting_revision_id=:expected)) AS origins,"
    " ((SELECT count(*) FROM oidc_trust_authority_lifecycle_changes"
    " WHERE expected_revision_id=:expected) +"
    " (SELECT count(*) FROM oidc_trust_authority_recoveries"
    " WHERE expected_revision_id=:expected)) AS successors"
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
_REACTIVATE = text(
    "UPDATE oidc_trust_management_authorities SET status='active'"
    " WHERE user_id=:target AND status='inactive'"
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
_INSERT_CURRENT = text(
    "INSERT INTO oidc_trust_authority_current_set (singleton_key,revision_id)"
    " VALUES (1,:revision)"
)
_INSERT_RECOVERY = text(
    "INSERT INTO oidc_trust_authority_recoveries"
    " (recovery_id,target_user_id,expected_revision_id,resulting_revision_id)"
    " VALUES (:recovery,:target,:expected,:revision)"
)
_SELECT_REVISION = text(
    "SELECT revision_id FROM oidc_trust_authority_set_revisions"
    " WHERE revision_id=:revision"
)


def _fail() -> None:
    raise OidcTrustAuthorityRecoveryUnavailable


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
        raise OidcTrustAuthorityRecoveryUnavailable from None
    if not decoded:
        _fail()
    return decoded


class DatabaseOfflineOidcTrustAuthorityRecovery:
    """Reactivate only eligible historical authority in a closed scope."""

    __slots__ = ("_engine", "_generate_revision_id")

    def __init__(
        self, engine: Engine, *,
        generate_revision_id: Callable[[], OidcTrustAuthoritySetRevisionId],
    ) -> None:
        self._engine = engine
        self._generate_revision_id = generate_revision_id

    def __repr__(self) -> str:
        return "DatabaseOfflineOidcTrustAuthorityRecovery()"

    def recover(
        self,
        recovery_id: OidcTrustAuthorityRecoveryId,
        target_user_id: UserId,
        expected_revision: OidcTrustAuthoritySetRevisionId,
    ) -> RecoveredOidcTrustAuthoritySet | None:
        try:
            return self._recover(recovery_id, target_user_id, expected_revision)
        except OidcTrustAuthorityRecoveryConflict as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure: type[Exception] = OidcTrustAuthorityRecoveryConflict
        except OidcTrustAuthorityRecoveryUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure = OidcTrustAuthorityRecoveryUnavailable
        except Exception:
            failure = OidcTrustAuthorityRecoveryUnavailable
        raise failure()

    def _recover(
        self,
        recovery_id: OidcTrustAuthorityRecoveryId,
        target_user_id: UserId,
        expected_revision: OidcTrustAuthoritySetRevisionId,
    ) -> RecoveredOidcTrustAuthoritySet | None:
        if (
            type(recovery_id) is not OidcTrustAuthorityRecoveryId
            or type(expected_revision) is not OidcTrustAuthoritySetRevisionId
        ):
            _fail()
        parameters = {
            "recovery": _encode(recovery_id.value),
            "target": _encode(target_user_id),
            "expected": _encode(expected_revision.value),
        }
        with self._engine.begin() as transaction:
            if transaction.dialect.name not in {"postgresql", "sqlite"}:
                _fail()
            existing = transaction.execute(_SELECT_RECOVERY, parameters).first()
            if existing is not None:
                return self._resolve(transaction, existing, recovery_id, parameters)
            if transaction.dialect.name == "postgresql":
                transaction.execute(_LOCK)
                existing = transaction.execute(
                    _SELECT_RECOVERY, parameters
                ).first()
                if existing is not None:
                    return self._resolve(
                        transaction, existing, recovery_id, parameters
                    )
            if transaction.execute(_TARGET, parameters).first() is None:
                return None
            current = transaction.execute(_CURRENT).first()
            has_current = current is not None
            if has_current:
                if _stored(current.revision_id) != parameters["expected"]:
                    return None
            else:
                terminal = transaction.execute(_TERMINAL, parameters).one()
                if terminal.origins != 1 or terminal.successors != 0:
                    return None
            inventory = transaction.execute(_INVENTORY).all()
            members = transaction.execute(_MEMBERS, parameters).all()
            snapshot = self._snapshot(inventory)
            if snapshot != self._snapshot(members):
                _fail()
            if any(
                row.status == "active" and row.user_status == "active"
                for row in inventory
            ):
                return None
            changed = [
                (user, "active" if user == parameters["target"] else status)
                for user, status in snapshot
            ]
            if transaction.execute(_REACTIVATE, parameters).rowcount != 1:
                _fail()
            revision_id = self._generate_revision_id()
            if type(revision_id) is not OidcTrustAuthoritySetRevisionId:
                _fail()
            revision = _encode(revision_id.value)
            values = dict(parameters, revision=revision)
            transaction.execute(_INSERT_REVISION, values)
            for user, status in changed:
                transaction.execute(
                    _INSERT_MEMBER, dict(values, user=user, status=status)
                )
            if has_current:
                if transaction.execute(_UPDATE_CURRENT, values).rowcount != 1:
                    _fail()
            else:
                transaction.execute(_INSERT_CURRENT, values)
            transaction.execute(_INSERT_RECOVERY, values)
            return RecoveredOidcTrustAuthoritySet(
                recovery_id, revision_id, target_user_id
            )

    @staticmethod
    def _snapshot(rows: list[Row[Any]]) -> list[tuple[bytes, str]]:
        result = []
        for row in rows:
            if row.status not in {"active", "inactive"}:
                _fail()
            result.append((_stored(row.user_id), row.status))
        return result

    @staticmethod
    def _resolve(
        transaction: Connection, row: Row[Any],
        recovery_id: OidcTrustAuthorityRecoveryId,
        parameters: dict[str, bytes],
    ) -> RecoveredOidcTrustAuthoritySet:
        if (
            _stored(row.target_user_id) != parameters["target"]
            or _stored(row.expected_revision_id) != parameters["expected"]
        ):
            raise OidcTrustAuthorityRecoveryConflict
        revision = _stored(row.resulting_revision_id)
        if transaction.execute(
            _SELECT_REVISION, {"revision": revision}
        ).first() is None:
            _fail()
        return RecoveredOidcTrustAuthoritySet(
            recovery_id,
            OidcTrustAuthoritySetRevisionId(_decode(revision)),
            UserId(_decode(parameters["target"])),
        )
