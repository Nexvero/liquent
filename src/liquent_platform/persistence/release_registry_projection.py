"""Canonical read-only projection of the current release-authority registry."""

from __future__ import annotations

import json

from sqlalchemy import Engine, text

from liquent_platform.identity.release_authority import (
    ReleasePromotionVerifierId,
    ReleaseSigningPublicKey,
)
from liquent_platform.persistence.identity_errors import (
    ReleaseRegistryProjectionUnavailable,
)


_CURRENT = text(
    "SELECT current.revision_id,revision.policy_revision_id,"
    " revision.policy_status FROM release_registry_current_set AS current"
    " JOIN release_registry_set_revisions AS revision"
    " ON revision.revision_id=current.revision_id WHERE current.singleton_key=1"
)
_SIGNERS = text(
    "SELECT member.authority_id,member.status FROM release_registry_revision_signers"
    " AS member WHERE member.revision_id=:revision ORDER BY member.authority_id"
)
_LIFECYCLE = text(
    "SELECT member.authority_id,member.status"
    " FROM release_registry_revision_lifecycle_authorities AS member"
    " WHERE member.revision_id=:revision ORDER BY member.authority_id"
)
_KEYS = text(
    "SELECT member.key_id,member.signer_authority_id,member.status,key.algorithm,"
    " key.namespace,key.fingerprint,key.public_key"
    " FROM release_registry_revision_keys AS member"
    " JOIN release_signing_keys AS key ON key.key_id=member.key_id"
    " AND key.signer_authority_id=member.signer_authority_id"
    " WHERE member.revision_id=:revision ORDER BY member.key_id"
)


def _decode(value: object) -> str:
    if not isinstance(value, bytes) or not value:
        raise ReleaseRegistryProjectionUnavailable
    return bytes(value).decode("utf-8")


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


class DatabaseCurrentReleaseAuthorityRegistryProjection:
    """Read and validate one complete current registry snapshot on every call."""

    __slots__ = ("_engine", "_verification_identity")

    def __init__(
        self, engine: Engine, *, verification_identity: ReleasePromotionVerifierId
    ) -> None:
        if type(verification_identity) is not ReleasePromotionVerifierId:
            raise ValueError("verification identity is invalid")
        self._engine = engine
        self._verification_identity = verification_identity

    def __repr__(self) -> str:
        return "DatabaseCurrentReleaseAuthorityRegistryProjection()"

    def project(self) -> bytes | None:
        try:
            with self._engine.connect() as raw:
                level = (
                    "REPEATABLE READ"
                    if raw.dialect.name == "postgresql"
                    else "SERIALIZABLE"
                )
                connection = raw.execution_options(isolation_level=level)
                with connection.begin():
                    current = connection.execute(_CURRENT).first()
                    if current is None:
                        return None
                    revision = bytes(current.revision_id)
                    signers = connection.execute(
                        _SIGNERS, {"revision": revision}
                    ).all()
                    lifecycle = connection.execute(
                        _LIFECYCLE, {"revision": revision}
                    ).all()
                    keys = connection.execute(_KEYS, {"revision": revision}).all()
                    counts = connection.execute(text(
                        "SELECT "
                        "(SELECT count(*) FROM release_signer_authorities),"
                        "(SELECT count(*) FROM release_registry_lifecycle_authorities),"
                        "(SELECT count(*) FROM release_signing_keys)"
                    )).one()
            return self._render(current, signers, lifecycle, keys, counts)
        except ReleaseRegistryProjectionUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ReleaseRegistryProjectionUnavailable

    def _render(self, current, signers, lifecycle, keys, counts) -> bytes:
        if counts != (len(signers), len(lifecycle), len(keys)):
            raise ReleaseRegistryProjectionUnavailable
        if not signers or not lifecycle:
            raise ReleaseRegistryProjectionUnavailable
        authorities: dict[str, dict[str, object]] = {}
        for row in signers:
            authority_id = _decode(row.authority_id)
            if row.status not in {"active", "inactive"} or authority_id in authorities:
                raise ReleaseRegistryProjectionUnavailable
            authorities[authority_id] = {
                "authority_id": authority_id,
                "status": row.status,
                "keys": [],
            }
        lifecycle_ids: set[str] = set()
        for row in lifecycle:
            authority_id = _decode(row.authority_id)
            if (
                row.status not in {"active", "inactive"}
                or authority_id in lifecycle_ids
            ):
                raise ReleaseRegistryProjectionUnavailable
            lifecycle_ids.add(authority_id)
        seen_keys: set[str] = set()
        seen_fingerprints: set[str] = set()
        for row in keys:
            key_id = _decode(row.key_id)
            signer_id = _decode(row.signer_authority_id)
            if (
                key_id in seen_keys
                or row.fingerprint in seen_fingerprints
                or signer_id not in authorities
                or row.status not in {"active", "inactive", "expired", "revoked"}
                or row.algorithm != "ssh-ed25519"
                or row.namespace != "liquent-operations-release-v1"
            ):
                raise ReleaseRegistryProjectionUnavailable
            ReleaseSigningPublicKey(row.fingerprint, row.public_key)
            seen_keys.add(key_id)
            seen_fingerprints.add(row.fingerprint)
            authorities[signer_id]["keys"].append({
                "key_id": key_id,
                "status": row.status,
                "fingerprint": row.fingerprint,
                "algorithm": row.algorithm,
                "namespaces": [row.namespace],
                "public_key": row.public_key,
            })
        if current.policy_status not in {"active", "inactive"}:
            raise ReleaseRegistryProjectionUnavailable
        return _canonical({
            "schema_version": 1,
            "policy_revision": _decode(current.policy_revision_id),
            "policy_status": current.policy_status,
            "verification_identity": self._verification_identity.value,
            "authorities": list(authorities.values()),
        })
