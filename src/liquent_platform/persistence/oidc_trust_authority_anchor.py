"""Controlled anchoring of existing global OIDC-trust bootstrap authority."""

from collections.abc import Callable
from typing import Any

from sqlalchemy import Connection, Engine, Row, text

from liquent_platform.identity.oidc_trust import (
    AnchoredOidcTrustAuthoritySet,
    OidcTrustAuthorityLifecycleChangeId,
    OidcTrustAuthoritySetRevisionId,
)
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_errors import (
    OidcTrustAuthorityAnchorConflict,
    OidcTrustAuthorityAnchorUnavailable,
)

_LOCK = text(
    "LOCK TABLE identity_users, oidc_trust_management_authorities,"
    " oidc_trust_authority_set_revisions, oidc_trust_authority_set_members,"
    " oidc_trust_authority_current_set, oidc_trust_authority_lifecycle_changes,"
    " oidc_trust_authority_recoveries IN SHARE ROW EXCLUSIVE MODE"
)
_SELECT_CHANGE = text(
    "SELECT * FROM oidc_trust_authority_lifecycle_changes WHERE change_id=:change"
)
_EMPTY = text(
    "SELECT NOT EXISTS (SELECT 1 FROM oidc_trust_authority_set_revisions)"
    " AND NOT EXISTS (SELECT 1 FROM oidc_trust_authority_current_set)"
    " AND NOT EXISTS (SELECT 1 FROM oidc_trust_authority_lifecycle_changes)"
    " AND NOT EXISTS (SELECT 1 FROM oidc_trust_authority_recoveries)"
)
_ACTOR = text(
    "SELECT 1 FROM identity_users AS users"
    " JOIN oidc_trust_management_authorities AS authority"
    " ON authority.user_id=users.user_id"
    " WHERE users.user_id=:actor AND users.status='active'"
    " AND authority.status='active'"
)
_INVENTORY = text(
    "SELECT authority.user_id,authority.status"
    " FROM oidc_trust_management_authorities AS authority"
    " JOIN identity_users AS users ON users.user_id=authority.user_id"
    " ORDER BY authority.user_id"
)
_INSERT_REVISION = text(
    "INSERT INTO oidc_trust_authority_set_revisions (revision_id)"
    " VALUES (:revision)"
)
_INSERT_MEMBER = text(
    "INSERT INTO oidc_trust_authority_set_members"
    " (revision_id,user_id,status) VALUES (:revision,:user,:status)"
)
_INSERT_CURRENT = text(
    "INSERT INTO oidc_trust_authority_current_set (singleton_key,revision_id)"
    " VALUES (1,:revision)"
)
_INSERT_CHANGE = text(
    "INSERT INTO oidc_trust_authority_lifecycle_changes"
    " (change_id,actor_user_id,target_user_id,intent,expected_revision_id,"
    " resulting_revision_id) VALUES (:change,:actor,:actor,'anchor',NULL,:revision)"
)
_SELECT_REVISION = text(
    "SELECT revision_id FROM oidc_trust_authority_set_revisions"
    " WHERE revision_id=:revision"
)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise OidcTrustAuthorityAnchorUnavailable
    return value.encode("utf-8")


def _stored(value: object) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)) or not value:
        raise OidcTrustAuthorityAnchorUnavailable
    return bytes(value)


def _decode(value: object) -> str:
    try:
        decoded = _stored(value).decode("utf-8")
    except UnicodeDecodeError:
        raise OidcTrustAuthorityAnchorUnavailable from None
    if not decoded:
        raise OidcTrustAuthorityAnchorUnavailable
    return decoded


class DatabaseOidcTrustAuthoritySetAnchor:
    """Create the first global set revision from current bootstrap facts."""

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
        return "DatabaseOidcTrustAuthoritySetAnchor()"

    def anchor(
        self,
        change_id: OidcTrustAuthorityLifecycleChangeId,
        principal: SessionPrincipal,
    ) -> AnchoredOidcTrustAuthoritySet | None:
        try:
            return self._anchor(change_id, principal)
        except OidcTrustAuthorityAnchorConflict as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure: type[Exception] = OidcTrustAuthorityAnchorConflict
        except OidcTrustAuthorityAnchorUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure = OidcTrustAuthorityAnchorUnavailable
        except Exception:
            failure = OidcTrustAuthorityAnchorUnavailable
        raise failure()

    def _anchor(
        self,
        change_id: OidcTrustAuthorityLifecycleChangeId,
        principal: SessionPrincipal,
    ) -> AnchoredOidcTrustAuthoritySet | None:
        if type(change_id) is not OidcTrustAuthorityLifecycleChangeId:
            raise OidcTrustAuthorityAnchorUnavailable
        if type(principal) is not SessionPrincipal:
            raise OidcTrustAuthorityAnchorUnavailable
        parameters = {
            "change": _encode(change_id.value),
            "actor": _encode(principal.user_id),
        }
        with self._engine.begin() as transaction:
            if transaction.dialect.name not in {"postgresql", "sqlite"}:
                raise OidcTrustAuthorityAnchorUnavailable
            existing = transaction.execute(_SELECT_CHANGE, parameters).first()
            if existing is not None:
                return self._resolve(transaction, existing, change_id, parameters)
            if transaction.dialect.name == "postgresql":
                transaction.execute(_LOCK)
                existing = transaction.execute(_SELECT_CHANGE, parameters).first()
                if existing is not None:
                    return self._resolve(
                        transaction, existing, change_id, parameters
                    )
            if not transaction.scalar(_EMPTY):
                return None
            if transaction.execute(_ACTOR, parameters).first() is None:
                return None
            inventory = transaction.execute(_INVENTORY).all()
            if not inventory:
                return None
            revision_id = self._generate_revision_id()
            if type(revision_id) is not OidcTrustAuthoritySetRevisionId:
                raise OidcTrustAuthorityAnchorUnavailable
            revision = _encode(revision_id.value)
            transaction.execute(_INSERT_REVISION, {"revision": revision})
            for member in inventory:
                transaction.execute(
                    _INSERT_MEMBER,
                    {
                        "revision": revision,
                        "user": _stored(member.user_id),
                        "status": member.status,
                    },
                )
            values = dict(parameters, revision=revision)
            transaction.execute(_INSERT_CURRENT, values)
            transaction.execute(_INSERT_CHANGE, values)
            return AnchoredOidcTrustAuthoritySet(change_id, revision_id)

    @staticmethod
    def _resolve(
        transaction: Connection,
        row: Row[Any],
        change_id: OidcTrustAuthorityLifecycleChangeId,
        parameters: dict[str, bytes],
    ) -> AnchoredOidcTrustAuthoritySet:
        if (
            _stored(row.actor_user_id) != parameters["actor"]
            or _stored(row.target_user_id) != parameters["actor"]
            or row.intent != "anchor"
            or row.expected_revision_id is not None
        ):
            raise OidcTrustAuthorityAnchorConflict
        revision = _stored(row.resulting_revision_id)
        if transaction.execute(
            _SELECT_REVISION, {"revision": revision}
        ).first() is None:
            raise OidcTrustAuthorityAnchorUnavailable
        return AnchoredOidcTrustAuthoritySet(
            change_id, OidcTrustAuthoritySetRevisionId(_decode(revision))
        )
