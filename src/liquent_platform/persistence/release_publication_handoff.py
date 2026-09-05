"""Atomic current-authority-bound release publication handoff."""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Connection, Engine, text

from liquent_platform.identity.ports import CurrentReleaseAuthorityRegistryProjection
from liquent_platform.identity.release_publication import (
    AcceptedReleasePublicationHandoff,
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublicationDecisionId,
    ReleasePublicationHandoffId,
    ReleasePublisherAuthorityId,
)
from liquent_platform.persistence.identity_errors import (
    ReleasePublicationHandoffConflict,
    ReleasePublicationHandoffUnavailable,
)
from tools.release_promotion_verifier import (
    PromotionRejected,
    PromotionUnavailable,
    verify_release_promotion_with_projection,
)


_LOCK = text(
    "LOCK TABLE release_registry_current_set,release_registry_set_revisions,"
    " release_registry_revision_signers,release_registry_revision_keys,"
    " release_signing_keys,release_publication_channels,"
    " release_publisher_authorities,release_publication_channel_revisions,"
    " release_publication_revision_publishers,"
    " release_publication_current_channels,release_publication_handoffs"
    " IN SHARE ROW EXCLUSIVE MODE"
)
_RETRY = text("SELECT * FROM release_publication_handoffs WHERE handoff_id=:handoff")
_CHANNEL = text(
    "SELECT revision.package_name FROM release_publication_current_channels current"
    " JOIN release_publication_channel_revisions revision"
    " ON revision.revision_id=current.revision_id"
    " AND revision.channel_id=current.channel_id AND revision.status='active'"
    " AND revision.artifact_class='operational_bundle'"
    " JOIN release_publication_revision_publishers publisher"
    " ON publisher.revision_id=current.revision_id"
    " AND publisher.channel_id=current.channel_id"
    " AND publisher.authority_id=:publisher AND publisher.status='active'"
    " WHERE current.channel_id=:channel AND current.revision_id=:channel_revision"
)
_RELEASE = text(
    "SELECT current.revision_id,revision.policy_revision_id,key.signer_authority_id"
    " FROM release_registry_current_set current JOIN release_registry_set_revisions revision"
    " ON revision.revision_id=current.revision_id AND revision.policy_status='active'"
    " JOIN release_registry_revision_keys member ON member.revision_id=current.revision_id"
    " AND member.key_id=:key AND member.status='active'"
    " JOIN release_signing_keys key ON key.key_id=member.key_id"
    " AND key.signer_authority_id=member.signer_authority_id"
    " JOIN release_registry_revision_signers signer ON signer.revision_id=current.revision_id"
    " AND signer.authority_id=key.signer_authority_id AND signer.status='active'"
    " WHERE current.singleton_key=1 AND key.signer_authority_id=:signer"
)


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _encode(value: str) -> bytes:
    if type(value) is not str or not value:
        raise ReleasePublicationHandoffUnavailable
    return value.encode()


def _read(path: str) -> bytes:
    item = Path(path)
    try:
        if item.is_symlink() or not item.is_file():
            raise ReleasePublicationHandoffUnavailable
        return item.read_bytes()
    except ReleasePublicationHandoffUnavailable:
        raise
    except OSError:
        raise ReleasePublicationHandoffUnavailable from None


def _evidence(value: bytes) -> dict[str, object]:
    try:
        result = json.loads(value)
    except (UnicodeError, json.JSONDecodeError):
        raise ReleasePublicationHandoffUnavailable from None
    if not isinstance(result, dict) or result.get("promotable") is not True:
        raise ReleasePublicationHandoffUnavailable
    if value != (json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii"):
        raise ReleasePublicationHandoffUnavailable
    return result


def _wheel_hash(bundle: bytes) -> str:
    try:
        with tarfile.open(fileobj=io.BytesIO(bundle), mode="r:gz") as archive:
            manifests = [item for item in archive.getmembers() if item.isfile() and item.name.endswith("/manifest.json")]
            if len(manifests) != 1:
                raise ReleasePublicationHandoffUnavailable
            opened = archive.extractfile(manifests[0])
            if opened is None:
                raise ReleasePublicationHandoffUnavailable
            manifest = json.loads(opened.read())
        wheel = manifest["wheel"]
        value = wheel["sha256"]
        if type(value) is not str or len(value) != 64:
            raise ReleasePublicationHandoffUnavailable
        return value
    except ReleasePublicationHandoffUnavailable:
        raise
    except Exception:
        raise ReleasePublicationHandoffUnavailable from None


class DatabaseAuthorizedReleasePublicationHandoff:
    __slots__ = ("_engine", "_projection", "_clock")

    def __init__(self, engine: Engine, *, registry_projection: CurrentReleaseAuthorityRegistryProjection, clock: Callable[[], datetime] | None = None) -> None:
        self._engine = engine
        self._projection = registry_projection
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return "DatabaseAuthorizedReleasePublicationHandoff()"

    def accept_handoff(self, handoff_id, decision_id, publisher_authority_id,
                       channel_id, expected_channel_revision, bundle_path,
                       signature_path, promotion_evidence_path):
        try:
            types = (
                type(handoff_id) is ReleasePublicationHandoffId,
                type(decision_id) is ReleasePublicationDecisionId,
                type(publisher_authority_id) is ReleasePublisherAuthorityId,
                type(channel_id) is ReleasePublicationChannelId,
                type(expected_channel_revision) is ReleasePublicationChannelPolicyRevisionId,
                type(bundle_path) is str and bool(bundle_path),
                type(signature_path) is str and bool(signature_path),
                type(promotion_evidence_path) is str and bool(promotion_evidence_path),
            )
            if not all(types):
                raise ReleasePublicationHandoffUnavailable
            bundle = _read(bundle_path)
            signature = _read(signature_path)
            supplied_bytes = _read(promotion_evidence_path)
            supplied = _evidence(supplied_bytes)
            values = {
                "handoff": _encode(handoff_id.value), "decision": _encode(decision_id.value),
                "publisher": _encode(publisher_authority_id.value), "channel": _encode(channel_id.value),
                "channel_revision": _encode(expected_channel_revision.value),
                "bundle_hash": _hash(bundle), "signature_hash": _hash(signature),
                "evidence_hash": _hash(supplied_bytes),
            }
            with self._engine.begin() as transaction:
                return self._accept(transaction, handoff_id, decision_id, channel_id,
                                    expected_channel_revision, Path(bundle_path),
                                    Path(signature_path), supplied, values, bundle)
        except (ReleasePublicationHandoffConflict, ReleasePublicationHandoffUnavailable) as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ReleasePublicationHandoffUnavailable

    def _accept(self, transaction: Connection, handoff_id, decision_id, channel_id,
                channel_revision, bundle_path, signature_path, supplied, values, bundle):
        if transaction.dialect.name == "postgresql":
            transaction.execute(_LOCK)
        elif transaction.dialect.name != "sqlite":
            raise ReleasePublicationHandoffUnavailable
        retry = transaction.execute(_RETRY, values).first()
        if retry is not None:
            if (retry.decision_id != values["decision"] or retry.channel_id != values["channel"]
                or retry.channel_revision_id != values["channel_revision"]
                or retry.bundle_sha256 != values["bundle_hash"]
                or retry.signature_sha256 != values["signature_hash"]
                or retry.promotion_evidence_sha256 != values["evidence_hash"]):
                raise ReleasePublicationHandoffConflict
            return AcceptedReleasePublicationHandoff(handoff_id, decision_id, channel_id, channel_revision)
        if transaction.execute(text("SELECT 1 FROM release_publication_handoffs WHERE decision_id=:decision"), values).first():
            raise ReleasePublicationHandoffConflict
        try:
            current = verify_release_promotion_with_projection(
                bundle_path=bundle_path, signature_path=signature_path,
                registry_projection=self._projection,
                key_id=str(supplied.get("key_id", "")),
            )
        except PromotionRejected:
            return None
        except PromotionUnavailable:
            raise ReleasePublicationHandoffUnavailable from None
        comparable = set(current) - {"decided_at"}
        if set(supplied) != set(current) or any(supplied[key] != current[key] for key in comparable):
            return None
        channel = transaction.execute(_CHANNEL, values).first()
        if channel is None or channel.package_name != "liquent":
            return None
        values.update({"key": _encode(current["key_id"]), "signer": _encode(current["signer_authority_id"])})
        release = transaction.execute(_RELEASE, values).first()
        if release is None or release.policy_revision_id.decode() != current["policy_revision"]:
            return None
        now = self._clock()
        promotion_time = datetime.fromisoformat(str(supplied["decided_at"]).replace("Z", "+00:00"))
        if not isinstance(now, datetime) or now.tzinfo is None or promotion_time.tzinfo is None:
            raise ReleasePublicationHandoffUnavailable
        values.update({
            "wheel_hash": _wheel_hash(bundle), "checksums_hash": current["checksums_sha256"],
            "commit": current["source_commit"], "version": current["package_version"],
            "format": current["bundle_format_version"], "registry": release.revision_id,
            "policy": release.policy_revision_id, "verifier": _encode(current["verification_identity"]),
            "promotion_time": promotion_time, "now": now.astimezone(timezone.utc),
        })
        transaction.execute(text(
            "INSERT INTO release_publication_handoffs VALUES "
            "(:handoff,:decision,:publisher,:channel,:channel_revision,:bundle_hash,"
            ":wheel_hash,:checksums_hash,:signature_hash,:evidence_hash,:commit,"
            ":version,:format,:signer,:key,:registry,:policy,:verifier,"
            ":promotion_time,:now,'ready_for_publication')"
        ), values)
        return AcceptedReleasePublicationHandoff(handoff_id, decision_id, channel_id, channel_revision)
