"""Atomic proof-bound activation of one inactive release signing key."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable

from sqlalchemy import Connection, Engine, text

from liquent_platform.identity.ports import (
    ReleaseKeyActivationApprovalVerifier,
    ReleaseKeyProofVerifier,
)
from liquent_platform.identity.release_authority import (
    ActivatedReleaseSigningKey,
    ReleaseActivationReviewerId,
    ReleaseRegistryLifecycleAuthorityId,
    ReleaseRegistryLifecycleChangeId,
    ReleaseRegistrySetRevisionId,
    ReleaseSigningKeyId,
)
from liquent_platform.persistence.identity_errors import (
    ReleaseKeyActivationConflict,
    ReleaseKeyActivationUnavailable,
)


_LOCK = text(
    "LOCK TABLE release_registry_current_set,release_registry_set_revisions,"
    " release_registry_revision_signers,"
    " release_registry_revision_lifecycle_authorities,"
    " release_registry_revision_keys,release_signing_keys,"
    " release_registry_lifecycle_changes,release_key_activations"
    " IN SHARE ROW EXCLUSIVE MODE"
)
_RETRY = text(
    "SELECT activation.actor_lifecycle_authority_id,activation.key_id,"
    " activation.expected_revision_id,activation.resulting_revision_id,"
    " activation.challenge_sha256,activation.proof_sha256,"
    " activation.approval_sha256,activation.reviewer_id"
    " FROM release_key_activations AS activation WHERE change_id=:change"
)
_CURRENT = text(
    "SELECT revision.policy_revision_id,key.signer_authority_id,key.fingerprint,"
    " key.public_key FROM release_registry_current_set AS current"
    " JOIN release_registry_set_revisions AS revision"
    " ON revision.revision_id=current.revision_id AND revision.policy_status='active'"
    " JOIN release_registry_revision_lifecycle_authorities AS actor"
    " ON actor.revision_id=current.revision_id"
    " AND actor.authority_id=:actor AND actor.status='active'"
    " JOIN release_registry_revision_keys AS key_member"
    " ON key_member.revision_id=current.revision_id"
    " AND key_member.key_id=:key AND key_member.status='inactive'"
    " JOIN release_signing_keys AS key ON key.key_id=key_member.key_id"
    " AND key.signer_authority_id=key_member.signer_authority_id"
    " JOIN release_registry_revision_signers AS signer"
    " ON signer.revision_id=current.revision_id"
    " AND signer.authority_id=key.signer_authority_id AND signer.status='active'"
    " WHERE current.singleton_key=1 AND current.revision_id=:expected"
)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise ReleaseKeyActivationUnavailable
    return value.encode("utf-8")


def _decode(value: object) -> str:
    if not isinstance(value, bytes) or not value:
        raise ReleaseKeyActivationUnavailable
    return bytes(value).decode("utf-8")


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _challenge(values: dict[str, str]) -> bytes:
    return (
        json.dumps(
            {
                "schema_version": 1,
                "namespace": "liquent-release-key-possession-v1",
                **values,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("ascii")


class DatabaseReleaseKeyActivationChallenge:
    """Resolve the exact current challenge without mutating registry state."""

    __slots__ = ("_engine",)

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def __repr__(self) -> str:
        return "DatabaseReleaseKeyActivationChallenge()"

    def get_challenge(
        self,
        change_id: ReleaseRegistryLifecycleChangeId,
        actor_authority_id: ReleaseRegistryLifecycleAuthorityId,
        key_id: ReleaseSigningKeyId,
        expected_revision: ReleaseRegistrySetRevisionId,
    ) -> bytes | None:
        try:
            if (
                type(change_id) is not ReleaseRegistryLifecycleChangeId
                or type(actor_authority_id) is not ReleaseRegistryLifecycleAuthorityId
                or type(key_id) is not ReleaseSigningKeyId
                or type(expected_revision) is not ReleaseRegistrySetRevisionId
            ):
                raise ReleaseKeyActivationUnavailable
            values = {
                "actor": _encode(actor_authority_id.value),
                "key": _encode(key_id.value),
                "expected": _encode(expected_revision.value),
            }
            with self._engine.connect() as connection:
                current = connection.execute(_CURRENT, values).first()
            if current is None:
                return None
            return _challenge({
                "actor_authority_id": actor_authority_id.value,
                "change_id": change_id.value,
                "expected_revision_id": expected_revision.value,
                "key_fingerprint": current.fingerprint,
                "key_id": key_id.value,
                "public_key_sha256": _hash(current.public_key.encode("ascii")),
            })
        except ReleaseKeyActivationUnavailable:
            raise
        except Exception:
            raise ReleaseKeyActivationUnavailable from None


class DatabaseReleaseKeyActivation:
    """Activate one current inactive key after proof and independent approval."""

    __slots__ = (
        "_engine",
        "_proof_verifier",
        "_approval_verifier",
        "_generate_revision_id",
    )

    def __init__(
        self,
        engine: Engine,
        *,
        proof_verifier: ReleaseKeyProofVerifier,
        approval_verifier: ReleaseKeyActivationApprovalVerifier,
        generate_revision_id: Callable[[], ReleaseRegistrySetRevisionId],
    ) -> None:
        self._engine = engine
        self._proof_verifier = proof_verifier
        self._approval_verifier = approval_verifier
        self._generate_revision_id = generate_revision_id

    def __repr__(self) -> str:
        return "DatabaseReleaseKeyActivation()"

    def activate_key(
        self,
        change_id: ReleaseRegistryLifecycleChangeId,
        actor_authority_id: ReleaseRegistryLifecycleAuthorityId,
        key_id: ReleaseSigningKeyId,
        expected_revision: ReleaseRegistrySetRevisionId,
        proof: bytes,
        approval: bytes,
    ) -> ActivatedReleaseSigningKey | None:
        try:
            if (
                type(change_id) is not ReleaseRegistryLifecycleChangeId
                or type(actor_authority_id) is not ReleaseRegistryLifecycleAuthorityId
                or type(key_id) is not ReleaseSigningKeyId
                or type(expected_revision) is not ReleaseRegistrySetRevisionId
                or type(proof) is not bytes
                or not proof
                or type(approval) is not bytes
                or not approval
            ):
                raise ReleaseKeyActivationUnavailable
            values = {
                "change": _encode(change_id.value),
                "actor": _encode(actor_authority_id.value),
                "key": _encode(key_id.value),
                "expected": _encode(expected_revision.value),
            }
            with self._engine.begin() as transaction:
                return self._activate(
                    transaction, change_id, actor_authority_id, key_id,
                    expected_revision, proof, approval, values,
                )
        except (ReleaseKeyActivationConflict, ReleaseKeyActivationUnavailable) as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ReleaseKeyActivationUnavailable

    def _activate(
        self, transaction: Connection,
        change_id: ReleaseRegistryLifecycleChangeId,
        actor_id: ReleaseRegistryLifecycleAuthorityId,
        key_id: ReleaseSigningKeyId,
        expected: ReleaseRegistrySetRevisionId,
        proof: bytes, approval: bytes, values: dict[str, bytes],
    ) -> ActivatedReleaseSigningKey | None:
        if transaction.dialect.name == "postgresql":
            transaction.execute(_LOCK)
        elif transaction.dialect.name != "sqlite":
            raise ReleaseKeyActivationUnavailable
        retry = transaction.execute(_RETRY, values).first()
        proof_hash = _hash(proof)
        approval_hash = _hash(approval)
        if retry is not None:
            return self._resolve_retry(
                change_id, actor_id, key_id, expected, proof_hash, approval_hash, retry
            )
        if transaction.execute(text(
            "SELECT 1 FROM release_registry_lifecycle_changes WHERE change_id=:change"
        ), values).first() is not None:
            raise ReleaseKeyActivationConflict
        current = transaction.execute(_CURRENT, values).first()
        if current is None:
            return None
        challenge = _challenge({
            "actor_authority_id": actor_id.value,
            "change_id": change_id.value,
            "expected_revision_id": expected.value,
            "key_fingerprint": current.fingerprint,
            "key_id": key_id.value,
            "public_key_sha256": _hash(current.public_key.encode("ascii")),
        })
        if self._proof_verifier.verify_proof(
            current.public_key, challenge, proof
        ) is not True:
            return None
        reviewer = self._approval_verifier.verify_approval(challenge, approval)
        if type(reviewer) is not ReleaseActivationReviewerId:
            return None
        if reviewer.value == actor_id.value:
            return None
        generated = self._generate_revision_id()
        if type(generated) is not ReleaseRegistrySetRevisionId:
            raise ReleaseKeyActivationUnavailable
        values.update({
            "resulting": _encode(generated.value),
            "policy": bytes(current.policy_revision_id),
            "reviewer": _encode(reviewer.value),
            "challenge_hash": _hash(challenge),
            "proof_hash": proof_hash,
            "approval_hash": approval_hash,
        })
        transaction.execute(text(
            "INSERT INTO release_registry_set_revisions VALUES "
            "(:resulting,:policy,'active')"
        ), values)
        transaction.execute(text(
            "INSERT INTO release_registry_revision_signers "
            "SELECT :resulting,authority_id,status FROM release_registry_revision_signers "
            "WHERE revision_id=:expected"
        ), values)
        transaction.execute(text(
            "INSERT INTO release_registry_revision_lifecycle_authorities "
            "SELECT :resulting,authority_id,status "
            "FROM release_registry_revision_lifecycle_authorities "
            "WHERE revision_id=:expected"
        ), values)
        transaction.execute(text(
            "INSERT INTO release_registry_revision_keys "
            "SELECT :resulting,key_id,signer_authority_id,"
            "CASE WHEN key_id=:key THEN 'active' ELSE status END "
            "FROM release_registry_revision_keys WHERE revision_id=:expected"
        ), values)
        transaction.execute(text(
            "INSERT INTO release_registry_lifecycle_changes VALUES "
            "(:change,:actor,'key',NULL,NULL,:key,'activate',:expected,:resulting)"
        ), values)
        transaction.execute(text(
            "INSERT INTO release_key_activations VALUES "
            "(:change,:actor,:key,:expected,:resulting,:challenge_hash,"
            ":proof_hash,:approval_hash,:reviewer)"
        ), values)
        updated = transaction.execute(text(
            "UPDATE release_registry_current_set SET revision_id=:resulting "
            "WHERE singleton_key=1 AND revision_id=:expected"
        ), values)
        if updated.rowcount != 1:
            raise ReleaseKeyActivationUnavailable
        return ActivatedReleaseSigningKey(change_id, key_id, generated, reviewer)

    @staticmethod
    def _resolve_retry(
        change_id: ReleaseRegistryLifecycleChangeId,
        actor_id: ReleaseRegistryLifecycleAuthorityId,
        key_id: ReleaseSigningKeyId,
        expected: ReleaseRegistrySetRevisionId,
        proof_hash: str, approval_hash: str, row: object,
    ) -> ActivatedReleaseSigningKey:
        if (
            _decode(row.actor_lifecycle_authority_id) != actor_id.value
            or _decode(row.key_id) != key_id.value
            or _decode(row.expected_revision_id) != expected.value
            or row.proof_sha256 != proof_hash
            or row.approval_sha256 != approval_hash
        ):
            raise ReleaseKeyActivationConflict
        return ActivatedReleaseSigningKey(
            change_id,
            key_id,
            ReleaseRegistrySetRevisionId(_decode(row.resulting_revision_id)),
            ReleaseActivationReviewerId(_decode(row.reviewer_id)),
        )
