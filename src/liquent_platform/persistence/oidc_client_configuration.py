"""Read the one currently active persistent OIDC client configuration."""

from __future__ import annotations

import json
from datetime import timedelta

from sqlalchemy import Engine, Row, text

from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.oidc_trust import (
    ActiveOidcTrustSnapshot,
    OidcTrustRevisionId,
)
from liquent_platform.persistence.identity_errors import (
    OidcClientConfigurationStoreUnavailable,
)

_SELECT = text("SELECT * FROM oidc_client_configuration WHERE singleton_key=1")


def _decode(value: object) -> str:
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise OidcClientConfigurationStoreUnavailable
    try:
        result = bytes(value).decode("utf-8")
    except UnicodeDecodeError:
        raise OidcClientConfigurationStoreUnavailable from None
    if not result:
        raise OidcClientConfigurationStoreUnavailable
    return result


def _decode_tuple(value: object) -> tuple[str, ...]:
    try:
        decoded = json.loads(_decode(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        raise OidcClientConfigurationStoreUnavailable from None
    if not isinstance(decoded, list) or any(type(item) is not str for item in decoded):
        raise OidcClientConfigurationStoreUnavailable
    return tuple(decoded)


class DatabaseActiveOidcClientConfiguration:
    """Resolve the server-owned singleton afresh for every trust decision."""

    __slots__ = ("_engine",)

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def __repr__(self) -> str:
        return "DatabaseActiveOidcClientConfiguration()"

    def get_active_configuration(self) -> TrustedOidcClientConfiguration | None:
        try:
            with self._engine.connect() as connection:
                row = connection.execute(_SELECT).first()
            if row is None or row.active in (False, 0):
                return None
            if row.active not in (True, 1):
                raise OidcClientConfigurationStoreUnavailable
            return self._restore(row)
        except OidcClientConfigurationStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise OidcClientConfigurationStoreUnavailable

    def get_active_trust(self) -> ActiveOidcTrustSnapshot | None:
        try:
            with self._engine.connect() as connection:
                row = connection.execute(_SELECT).first()
            if row is None or row.active in (False, 0):
                return None
            if row.active not in (True, 1):
                raise OidcClientConfigurationStoreUnavailable
            if row.revision_id is None:
                raise OidcClientConfigurationStoreUnavailable
            return ActiveOidcTrustSnapshot(
                OidcTrustRevisionId(_decode(row.revision_id)), self._restore(row)
            )
        except OidcClientConfigurationStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise OidcClientConfigurationStoreUnavailable

    @staticmethod
    def _restore(row: Row[object]) -> TrustedOidcClientConfiguration:
        skew = row.clock_skew_microseconds
        if type(skew) is not int:
            raise OidcClientConfigurationStoreUnavailable
        try:
            return TrustedOidcClientConfiguration(
                issuer=_decode(row.issuer),
                authorization_endpoint=_decode(row.authorization_endpoint),
                client_id=_decode(row.client_id),
                redirect_uri=_decode(row.redirect_uri),
                scopes=_decode_tuple(row.scopes),
                token_endpoint=_decode(row.token_endpoint),
                jwks_uri=_decode(row.jwks_uri),
                allowed_signing_algorithms=_decode_tuple(
                    row.allowed_signing_algorithms
                ),
                clock_skew=timedelta(microseconds=skew),
            )
        except (TypeError, ValueError, OverflowError):
            raise OidcClientConfigurationStoreUnavailable from None
