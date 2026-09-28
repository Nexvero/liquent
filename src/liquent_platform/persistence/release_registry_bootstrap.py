"""One-time atomic bootstrap of the persistent release-authority registry."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import Connection, Engine, text

from liquent_platform.identity.release_authority import (
    BootstrappedReleaseRegistry,
    ReleasePolicyRevisionId,
    ReleaseRegistryBootstrapId,
    ReleaseRegistryLifecycleAuthorityId,
    ReleaseRegistrySetRevisionId,
    ReleaseSignerAuthorityId,
    ReleaseSigningKeyId,
    ReleaseSigningPublicKey,
)
from liquent_platform.persistence.identity_errors import (
    ReleaseRegistryBootstrapConflict,
    ReleaseRegistryBootstrapUnavailable,
)


_TABLES = (
    "release_signer_authorities",
    "release_registry_lifecycle_authorities",
    "release_signing_keys",
    "release_registry_set_revisions",
    "release_registry_revision_signers",
    "release_registry_revision_lifecycle_authorities",
    "release_registry_revision_keys",
    "release_registry_current_set",
    "release_registry_lifecycle_changes",
    "release_signing_decisions",
    "release_registry_bootstraps",
)
_LOCK = text(
    "LOCK TABLE " + ", ".join(_TABLES) + " IN SHARE ROW EXCLUSIVE MODE"
)
_HAS_INVENTORY = text(
    "SELECT " + " OR ".join(
        f"EXISTS (SELECT 1 FROM {table})" for table in _TABLES
    )
)
_EXISTING = text(
    "SELECT bootstrap.lifecycle_authority_id,bootstrap.signer_authority_id,"
    " bootstrap.key_id,bootstrap.registry_revision_id,"
    " bootstrap.policy_revision_id,key.fingerprint,key.public_key,"
    " revision.policy_status,signer.status AS signer_status,"
    " lifecycle.status AS lifecycle_status,key_member.status AS key_status"
    " FROM release_registry_bootstraps AS bootstrap"
    " JOIN release_signing_keys AS key ON key.key_id=bootstrap.key_id"
    " AND key.signer_authority_id=bootstrap.signer_authority_id"
    " JOIN release_registry_set_revisions AS revision"
    " ON revision.revision_id=bootstrap.registry_revision_id"
    " AND revision.policy_revision_id=bootstrap.policy_revision_id"
    " JOIN release_registry_revision_signers AS signer"
    " ON signer.revision_id=bootstrap.registry_revision_id"
    " AND signer.authority_id=bootstrap.signer_authority_id"
    " JOIN release_registry_revision_lifecycle_authorities AS lifecycle"
    " ON lifecycle.revision_id=bootstrap.registry_revision_id"
    " AND lifecycle.authority_id=bootstrap.lifecycle_authority_id"
    " JOIN release_registry_revision_keys AS key_member"
    " ON key_member.revision_id=bootstrap.registry_revision_id"
    " AND key_member.key_id=bootstrap.key_id"
    " AND key_member.signer_authority_id=bootstrap.signer_authority_id"
    " WHERE bootstrap.bootstrap_id=:bootstrap"
)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise ReleaseRegistryBootstrapUnavailable
    return value.encode("utf-8")


def _stored(value: object) -> bytes:
    if not isinstance(value, bytes) or not value:
        raise ReleaseRegistryBootstrapUnavailable
    return bytes(value)


class DatabaseInitialReleaseRegistryBootstrap:
    """Create one inactive-key release registry exactly once."""

    __slots__ = (
        "_engine",
        "_generate_lifecycle_authority_id",
        "_generate_signer_authority_id",
        "_generate_key_id",
        "_generate_registry_revision_id",
        "_generate_policy_revision_id",
    )

    def __init__(
        self,
        engine: Engine,
        *,
        generate_lifecycle_authority_id: Callable[
            [], ReleaseRegistryLifecycleAuthorityId
        ],
        generate_signer_authority_id: Callable[[], ReleaseSignerAuthorityId],
        generate_key_id: Callable[[], ReleaseSigningKeyId],
        generate_registry_revision_id: Callable[[], ReleaseRegistrySetRevisionId],
        generate_policy_revision_id: Callable[[], ReleasePolicyRevisionId],
    ) -> None:
        self._engine = engine
        self._generate_lifecycle_authority_id = generate_lifecycle_authority_id
        self._generate_signer_authority_id = generate_signer_authority_id
        self._generate_key_id = generate_key_id
        self._generate_registry_revision_id = generate_registry_revision_id
        self._generate_policy_revision_id = generate_policy_revision_id

    def __repr__(self) -> str:
        return "DatabaseInitialReleaseRegistryBootstrap()"

    def bootstrap(
        self,
        bootstrap_id: ReleaseRegistryBootstrapId,
        public_key: ReleaseSigningPublicKey,
    ) -> BootstrappedReleaseRegistry | None:
        try:
            if type(bootstrap_id) is not ReleaseRegistryBootstrapId:
                raise ReleaseRegistryBootstrapUnavailable
            if type(public_key) is not ReleaseSigningPublicKey:
                raise ReleaseRegistryBootstrapUnavailable
            stored_bootstrap = _encode(bootstrap_id.value)
            with self._engine.begin() as transaction:
                return self._bootstrap(
                    transaction, bootstrap_id, stored_bootstrap, public_key
                )
        except (
            ReleaseRegistryBootstrapConflict,
            ReleaseRegistryBootstrapUnavailable,
        ) as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ReleaseRegistryBootstrapUnavailable

    def _bootstrap(
        self,
        transaction: Connection,
        bootstrap_id: ReleaseRegistryBootstrapId,
        stored_bootstrap: bytes,
        public_key: ReleaseSigningPublicKey,
    ) -> BootstrappedReleaseRegistry | None:
        if transaction.dialect.name == "postgresql":
            transaction.execute(_LOCK)
        elif transaction.dialect.name != "sqlite":
            raise ReleaseRegistryBootstrapUnavailable

        existing = transaction.execute(
            _EXISTING, {"bootstrap": stored_bootstrap}
        ).first()
        if existing is not None:
            return self._resolve_existing(bootstrap_id, public_key, existing)
        if transaction.scalar(_HAS_INVENTORY):
            return None

        lifecycle = self._generate_lifecycle_authority_id()
        signer = self._generate_signer_authority_id()
        key = self._generate_key_id()
        revision = self._generate_registry_revision_id()
        policy = self._generate_policy_revision_id()
        if type(lifecycle) is not ReleaseRegistryLifecycleAuthorityId:
            raise ReleaseRegistryBootstrapUnavailable
        if type(signer) is not ReleaseSignerAuthorityId:
            raise ReleaseRegistryBootstrapUnavailable
        if type(key) is not ReleaseSigningKeyId:
            raise ReleaseRegistryBootstrapUnavailable
        if type(revision) is not ReleaseRegistrySetRevisionId:
            raise ReleaseRegistryBootstrapUnavailable
        if type(policy) is not ReleasePolicyRevisionId:
            raise ReleaseRegistryBootstrapUnavailable
        values = {
            "bootstrap": stored_bootstrap,
            "lifecycle": _encode(lifecycle.value),
            "signer": _encode(signer.value),
            "key": _encode(key.value),
            "revision": _encode(revision.value),
            "policy": _encode(policy.value),
            "fingerprint": public_key.fingerprint,
            "public_key": public_key.public_key,
        }
        transaction.execute(text(
            "INSERT INTO release_registry_lifecycle_authorities VALUES (:lifecycle)"
        ), values)
        transaction.execute(text(
            "INSERT INTO release_signer_authorities VALUES (:signer)"
        ), values)
        transaction.execute(text(
            "INSERT INTO release_signing_keys VALUES "
            "(:key,:signer,'ssh-ed25519','liquent-operations-release-v1',"
            ":fingerprint,:public_key)"
        ), values)
        transaction.execute(text(
            "INSERT INTO release_registry_set_revisions VALUES "
            "(:revision,:policy,'active')"
        ), values)
        transaction.execute(text(
            "INSERT INTO release_registry_revision_signers VALUES "
            "(:revision,:signer,'active')"
        ), values)
        transaction.execute(text(
            "INSERT INTO release_registry_revision_lifecycle_authorities VALUES "
            "(:revision,:lifecycle,'active')"
        ), values)
        transaction.execute(text(
            "INSERT INTO release_registry_revision_keys VALUES "
            "(:revision,:key,:signer,'inactive')"
        ), values)
        transaction.execute(text(
            "INSERT INTO release_registry_current_set VALUES (1,:revision)"
        ), values)
        transaction.execute(text(
            "INSERT INTO release_registry_bootstraps VALUES "
            "(:bootstrap,:lifecycle,:signer,:key,:revision,:policy)"
        ), values)
        return BootstrappedReleaseRegistry(
            bootstrap_id, lifecycle, signer, key, revision, policy
        )

    @staticmethod
    def _resolve_existing(
        bootstrap_id: ReleaseRegistryBootstrapId,
        public_key: ReleaseSigningPublicKey,
        row: object,
    ) -> BootstrappedReleaseRegistry:
        if (
            row.fingerprint != public_key.fingerprint
            or row.public_key != public_key.public_key
        ):
            raise ReleaseRegistryBootstrapConflict
        if (
            row.policy_status != "active"
            or row.signer_status != "active"
            or row.lifecycle_status != "active"
            or row.key_status != "inactive"
        ):
            raise ReleaseRegistryBootstrapUnavailable
        lifecycle = ReleaseRegistryLifecycleAuthorityId(
            _stored(row.lifecycle_authority_id).decode("utf-8")
        )
        signer = ReleaseSignerAuthorityId(
            _stored(row.signer_authority_id).decode("utf-8")
        )
        key = ReleaseSigningKeyId(_stored(row.key_id).decode("utf-8"))
        revision = ReleaseRegistrySetRevisionId(
            _stored(row.registry_revision_id).decode("utf-8")
        )
        policy = ReleasePolicyRevisionId(
            _stored(row.policy_revision_id).decode("utf-8")
        )
        return BootstrappedReleaseRegistry(
            bootstrap_id, lifecycle, signer, key, revision, policy
        )
