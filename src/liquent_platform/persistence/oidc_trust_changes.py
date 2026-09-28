"""Atomic authorized activation, rotation, and deactivation of OIDC trust."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from sqlalchemy import Connection, Engine, Row, text
from sqlalchemy.exc import IntegrityError

from liquent_platform.identity.access import UserId
from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.oidc_trust import (
    AuthorizedOidcTrustChange,
    OidcTrustChangeId,
    OidcTrustChangeKind,
    OidcTrustRevisionId,
)
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_errors import (
    OidcTrustChangeConflict,
    OidcTrustChangeStoreUnavailable,
)

_SELECT_CHANGE = text(
    "SELECT change_id,actor_user_id,kind,expected_revision_id,"
    " resulting_revision_id FROM authorized_oidc_trust_changes"
    " WHERE change_id=:change"
)
_PERMITS = text(
    "SELECT 1 FROM identity_users AS actor"
    " JOIN oidc_trust_management_authorities AS authority"
    " ON authority.user_id=actor.user_id"
    " WHERE actor.user_id=:actor AND actor.status='active'"
    " AND authority.status='active'"
)
_PERMITS_POSTGRES = text(str(_PERMITS) + " FOR UPDATE OF actor, authority")
_ACTIVE = text(
    "SELECT * FROM oidc_client_configuration WHERE singleton_key=1"
)
_ACTIVE_POSTGRES = text(str(_ACTIVE) + " FOR UPDATE")
_INSERT_REVISION = text(
    "INSERT INTO oidc_trust_revisions"
    " (revision_id,issuer,authorization_endpoint,client_id,redirect_uri,scopes,"
    " token_endpoint,jwks_uri,allowed_signing_algorithms,clock_skew_microseconds)"
    " VALUES (:revision,:issuer,:authorization,:client,:redirect,:scopes,"
    " :token,:jwks,:algorithms,:skew)"
)
_UPSERT_ACTIVE = text(
    "INSERT INTO oidc_client_configuration"
    " (singleton_key,active,issuer,authorization_endpoint,client_id,redirect_uri,"
    " scopes,token_endpoint,jwks_uri,allowed_signing_algorithms,"
    " clock_skew_microseconds,revision_id) VALUES"
    " (1,true,:issuer,:authorization,:client,:redirect,:scopes,:token,:jwks,"
    " :algorithms,:skew,:revision) ON CONFLICT (singleton_key) DO UPDATE SET"
    " active=true,issuer=excluded.issuer,"
    " authorization_endpoint=excluded.authorization_endpoint,"
    " client_id=excluded.client_id,redirect_uri=excluded.redirect_uri,"
    " scopes=excluded.scopes,token_endpoint=excluded.token_endpoint,"
    " jwks_uri=excluded.jwks_uri,"
    " allowed_signing_algorithms=excluded.allowed_signing_algorithms,"
    " clock_skew_microseconds=excluded.clock_skew_microseconds,"
    " revision_id=excluded.revision_id"
)
_DEACTIVATE = text(
    "UPDATE oidc_client_configuration SET active=false"
    " WHERE singleton_key=1 AND active=true AND revision_id=:expected"
)
_INSERT_CHANGE = text(
    "INSERT INTO authorized_oidc_trust_changes"
    " (change_id,actor_user_id,kind,expected_revision_id,resulting_revision_id)"
    " VALUES (:change,:actor,:kind,:expected,:resulting)"
)
_SELECT_REVISION = text(
    "SELECT * FROM oidc_trust_revisions WHERE revision_id=:revision"
)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise OidcTrustChangeStoreUnavailable
    return value.encode("utf-8")


def _stored(value: object) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)) or not value:
        raise OidcTrustChangeStoreUnavailable
    return bytes(value)


def _decode(value: object) -> str:
    try:
        decoded = _stored(value).decode("utf-8")
    except UnicodeDecodeError:
        raise OidcTrustChangeStoreUnavailable from None
    if not decoded:
        raise OidcTrustChangeStoreUnavailable
    return decoded


def _configuration_values(
    configuration: TrustedOidcClientConfiguration,
) -> dict[str, object]:
    return {
        "issuer": _encode(configuration.issuer),
        "authorization": _encode(configuration.authorization_endpoint),
        "client": _encode(configuration.client_id),
        "redirect": _encode(configuration.redirect_uri),
        "scopes": json.dumps(
            list(configuration.scopes), separators=(",", ":")
        ).encode(),
        "token": _encode(configuration.token_endpoint),
        "jwks": _encode(configuration.jwks_uri),
        "algorithms": json.dumps(
            list(configuration.allowed_signing_algorithms), separators=(",", ":")
        ).encode(),
        "skew": configuration.clock_skew // timedelta(microseconds=1),
    }


def _restore_configuration(row: Row[Any]) -> TrustedOidcClientConfiguration:
    try:
        scopes = json.loads(_decode(row.scopes))
        algorithms = json.loads(_decode(row.allowed_signing_algorithms))
        if not isinstance(scopes, list) or not isinstance(algorithms, list):
            raise OidcTrustChangeStoreUnavailable
        return TrustedOidcClientConfiguration(
            issuer=_decode(row.issuer),
            authorization_endpoint=_decode(row.authorization_endpoint),
            client_id=_decode(row.client_id),
            redirect_uri=_decode(row.redirect_uri),
            scopes=tuple(scopes),
            token_endpoint=_decode(row.token_endpoint),
            jwks_uri=_decode(row.jwks_uri),
            allowed_signing_algorithms=tuple(algorithms),
            clock_skew=timedelta(microseconds=row.clock_skew_microseconds),
        )
    except (TypeError, ValueError, OverflowError, json.JSONDecodeError):
        raise OidcTrustChangeStoreUnavailable from None


class DatabaseAuthorizedOidcTrustChanges:
    """Order authority, state transition, revision, and retry decision."""

    __slots__ = ("_engine", "_generate_revision_id")

    def __init__(
        self,
        engine: Engine,
        *,
        generate_revision_id: Callable[[], OidcTrustRevisionId],
    ) -> None:
        self._engine = engine
        self._generate_revision_id = generate_revision_id

    def __repr__(self) -> str:
        return "DatabaseAuthorizedOidcTrustChanges()"

    def change_trust(
        self,
        change_id: OidcTrustChangeId,
        principal: SessionPrincipal,
        kind: OidcTrustChangeKind,
        expected_revision: OidcTrustRevisionId | None,
        configuration: TrustedOidcClientConfiguration | None,
    ) -> AuthorizedOidcTrustChange | None:
        try:
            return self._change(
                change_id, principal, kind, expected_revision, configuration
            )
        except OidcTrustChangeConflict as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure: type[Exception] = OidcTrustChangeConflict
        except OidcTrustChangeStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure = OidcTrustChangeStoreUnavailable
        except Exception:
            failure = OidcTrustChangeStoreUnavailable
        raise failure()

    def _change(
        self,
        change_id: OidcTrustChangeId,
        principal: SessionPrincipal,
        kind: OidcTrustChangeKind,
        expected_revision: OidcTrustRevisionId | None,
        configuration: TrustedOidcClientConfiguration | None,
    ) -> AuthorizedOidcTrustChange | None:
        self._validate_shape(kind, expected_revision, configuration)
        change = _encode(change_id.value)
        actor = _encode(principal.user_id)
        expected = None if expected_revision is None else _encode(expected_revision.value)

        with self._engine.begin() as transaction:
            if transaction.dialect.name not in {"postgresql", "sqlite"}:
                raise OidcTrustChangeStoreUnavailable
            existing = transaction.execute(
                _SELECT_CHANGE, {"change": change}
            ).first()
            if existing is not None:
                return self._resolve(
                    transaction, existing, change_id, actor, kind, expected,
                    configuration,
                )

            if transaction.dialect.name == "postgresql":
                transaction.execute(text(
                    "LOCK TABLE authorized_oidc_trust_changes,"
                    " oidc_client_configuration IN SHARE ROW EXCLUSIVE MODE"
                ))
                # A concurrent exact attempt may have committed while this
                # transaction waited. Resolve it before current authority or
                # transition state, exactly like any later technical retry.
                existing = transaction.execute(
                    _SELECT_CHANGE, {"change": change}
                ).first()
                if existing is not None:
                    return self._resolve(
                        transaction, existing, change_id, actor, kind, expected,
                        configuration,
                    )
            permits = (
                _PERMITS_POSTGRES
                if transaction.dialect.name == "postgresql"
                else _PERMITS
            )
            if transaction.execute(permits, {"actor": actor}).first() is None:
                return None

            active_query = (
                _ACTIVE_POSTGRES
                if transaction.dialect.name == "postgresql"
                else _ACTIVE
            )
            active = transaction.execute(active_query).first()
            if not self._transition_allowed(active, kind, expected):
                return None

            resulting: OidcTrustRevisionId | None = None
            if configuration is not None:
                resulting = self._generate_revision_id()
                if type(resulting) is not OidcTrustRevisionId:
                    raise OidcTrustChangeStoreUnavailable
                values = _configuration_values(configuration)
                values["revision"] = _encode(resulting.value)
                transaction.execute(_INSERT_REVISION, values)
                transaction.execute(_UPSERT_ACTIVE, values)
            elif transaction.execute(
                _DEACTIVATE, {"expected": expected}
            ).rowcount != 1:
                raise OidcTrustChangeStoreUnavailable

            try:
                transaction.execute(
                    _INSERT_CHANGE,
                    {
                        "change": change,
                        "actor": actor,
                        "kind": kind.value,
                        "expected": expected,
                        "resulting": (
                            None if resulting is None else _encode(resulting.value)
                        ),
                    },
                )
            except IntegrityError:
                raise OidcTrustChangeStoreUnavailable from None
            return AuthorizedOidcTrustChange(change_id, kind, resulting)

    @staticmethod
    def _validate_shape(
        kind: OidcTrustChangeKind,
        expected: OidcTrustRevisionId | None,
        configuration: TrustedOidcClientConfiguration | None,
    ) -> None:
        if type(kind) is not OidcTrustChangeKind:
            raise OidcTrustChangeStoreUnavailable
        valid = (
            kind is OidcTrustChangeKind.ACTIVATE
            and expected is None
            and type(configuration) is TrustedOidcClientConfiguration
        ) or (
            kind is OidcTrustChangeKind.ROTATE
            and type(expected) is OidcTrustRevisionId
            and type(configuration) is TrustedOidcClientConfiguration
        ) or (
            kind is OidcTrustChangeKind.DEACTIVATE
            and type(expected) is OidcTrustRevisionId
            and configuration is None
        )
        if not valid:
            raise OidcTrustChangeStoreUnavailable

    @staticmethod
    def _transition_allowed(
        active: Row[Any] | None,
        kind: OidcTrustChangeKind,
        expected: bytes | None,
    ) -> bool:
        if kind is OidcTrustChangeKind.ACTIVATE:
            return active is None
        if active is None or active.revision_id is None:
            return False
        if _stored(active.revision_id) != expected:
            return False
        if kind is OidcTrustChangeKind.DEACTIVATE:
            return active.active in (True, 1)
        return active.active in (True, 1, False, 0)

    @staticmethod
    def _resolve(
        transaction: Connection,
        row: Row[Any],
        change_id: OidcTrustChangeId,
        actor: bytes,
        kind: OidcTrustChangeKind,
        expected: bytes | None,
        configuration: TrustedOidcClientConfiguration | None,
    ) -> AuthorizedOidcTrustChange:
        stored_expected = (
            None if row.expected_revision_id is None
            else _stored(row.expected_revision_id)
        )
        if (
            _stored(row.actor_user_id) != actor
            or row.kind != kind.value
            or stored_expected != expected
        ):
            raise OidcTrustChangeConflict
        resulting = (
            None if row.resulting_revision_id is None
            else OidcTrustRevisionId(_decode(row.resulting_revision_id))
        )
        if configuration is None:
            if resulting is not None:
                raise OidcTrustChangeConflict
        else:
            if resulting is None:
                raise OidcTrustChangeConflict
            revision = transaction.execute(
                _SELECT_REVISION, {"revision": _encode(resulting.value)}
            ).first()
            if revision is None or _restore_configuration(revision) != configuration:
                raise OidcTrustChangeConflict
        return AuthorizedOidcTrustChange(change_id, kind, resulting)
