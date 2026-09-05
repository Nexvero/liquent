"""Canonical codec for one immutable pre-create wrapper launch binding."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from liquent_platform.identity.manifest_handoff import (
    ManifestHandoffExecutionClaimId,
    ManifestHandoffExecutionOwnerId,
    ManifestHandoffName,
    ManifestHandoffRecoveryClaimId,
    ManifestHandoffRecoveryOwnerId,
    ManifestHandoffRegistryScopeId,
    ManifestHandoffScopeBinding,
)
from liquent_platform.identity.manifest_handoff_supervisor import (
    ManifestHandoffRecoverySupervisorRequest,
    ManifestHandoffSupervisorHandleId,
    ManifestHandoffWriterSupervisorRequest,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_artifact import (
    ManifestHandoffSupervisorControlArtifactBytes,
)
from liquent_platform.identity.manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorTerminalObservationId,
)
from liquent_platform.identity.manifest_handoff_supervisor_engine import (
    ManifestHandoffSupervisorEngineProfile,
)
from liquent_platform.identity.manifest_handoff_supervisor_gate_wrapper import (
    StartManifestHandoffSupervisorGateWrapper,
)
from liquent_platform.identity.manifest_handoff_supervisor_journal import (
    ManifestHandoffSupervisorGatedObservationId,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_document import (
    EncodedManifestHandoffSupervisorLaunchDocument,
    ManifestHandoffSupervisorLaunchDocument,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactFacts,
    ManifestHandoffSupervisorControlArtifactId,
    ManifestHandoffSupervisorControlDirectoryId,
    ManifestHandoffSupervisorCreationId,
    ManifestHandoffSupervisorImageDigest,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_SCHEMA = "liquent.manifest-handoff-supervisor-launch"
_VERSION = 1
_MAXIMUM = 65_536
_KEYS = {
    "schema", "version", "document_id", "creation_id", "handle_id",
    "control_directory_id", "profile", "image_digest", "ready_artifact_id",
    "gated_observation_id", "consumed_artifact_id", "terminal_artifact_id",
    "terminal_observation_id", "claim_id", "owner_id", "scope_id",
    "source_root", "target_root", "handoff_name",
}


class CanonicalManifestHandoffSupervisorLaunchDocumentCodec:
    def __repr__(self) -> str:
        return "CanonicalManifestHandoffSupervisorLaunchDocumentCodec()"

    def encode(self, document):
        if type(document) is not ManifestHandoffSupervisorLaunchDocument:
            raise ManifestHandoffRegistryUnavailable
        try:
            gate, request = document.gate, document.request
            value = {
                "schema": _SCHEMA,
                "version": _VERSION,
                "document_id": document.document_id.value,
                "creation_id": document.creation_id.value,
                "handle_id": gate.handle_id.value,
                "control_directory_id": gate.control_directory_id.value,
                "profile": gate.profile.value,
                "image_digest": document.image_digest.value,
                "ready_artifact_id": gate.ready_artifact_id.value,
                "gated_observation_id": gate.gated_observation_id.value,
                "consumed_artifact_id": gate.consumed_artifact_id.value,
                "terminal_artifact_id": gate.terminal_artifact_id.value,
                "terminal_observation_id": gate.terminal_observation_id.value,
                "claim_id": request.claim_id.value,
                "owner_id": request.owner_id.value,
                "scope_id": request.binding.scope_id.value,
                "source_root": str(request.binding.source_root),
                "target_root": str(request.binding.target_root),
                "handoff_name": request.handoff_name.value,
            }
            content = json.dumps(
                value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                allow_nan=False,
            ).encode("utf-8")
            facts = ManifestHandoffSupervisorControlArtifactFacts(
                hashlib.sha256(content).hexdigest(), len(content)
            )
            return EncodedManifestHandoffSupervisorLaunchDocument(
                document, ManifestHandoffSupervisorControlArtifactBytes(content), facts
            )
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def decode(self, encoded):
        if type(encoded) is not EncodedManifestHandoffSupervisorLaunchDocument:
            raise ManifestHandoffRegistryUnavailable
        document = self.decode_content(encoded.content.value)
        if document != encoded.document or self.encode(document).content != encoded.content:
            raise ManifestHandoffRegistryUnavailable
        return document

    def decode_content(self, content):
        try:
            if type(content) is not bytes or not content or len(content) > _MAXIMUM:
                raise ManifestHandoffRegistryUnavailable
            value = json.loads(content.decode("utf-8"), object_pairs_hook=_unique)
            if (
                type(value) is not dict or set(value) != _KEYS
                or value["schema"] != _SCHEMA or type(value["version"]) is not int
                or value["version"] != _VERSION
            ):
                raise ManifestHandoffRegistryUnavailable
            profile = ManifestHandoffSupervisorEngineProfile(value["profile"])
            gate = StartManifestHandoffSupervisorGateWrapper(
                ManifestHandoffSupervisorHandleId(value["handle_id"]),
                ManifestHandoffSupervisorControlDirectoryId(value["control_directory_id"]),
                profile,
                ManifestHandoffSupervisorControlArtifactId(value["ready_artifact_id"]),
                ManifestHandoffSupervisorGatedObservationId(value["gated_observation_id"]),
                ManifestHandoffSupervisorControlArtifactId(value["consumed_artifact_id"]),
                ManifestHandoffSupervisorControlArtifactId(value["terminal_artifact_id"]),
                ManifestHandoffSupervisorTerminalObservationId(value["terminal_observation_id"]),
            )
            binding = ManifestHandoffScopeBinding(
                ManifestHandoffRegistryScopeId(value["scope_id"]),
                Path(value["source_root"]), Path(value["target_root"]),
            )
            name = ManifestHandoffName(value["handoff_name"])
            if profile is ManifestHandoffSupervisorEngineProfile.WRITER:
                request = ManifestHandoffWriterSupervisorRequest(
                    ManifestHandoffExecutionClaimId(value["claim_id"]),
                    ManifestHandoffExecutionOwnerId(value["owner_id"]), binding, name,
                )
            else:
                request = ManifestHandoffRecoverySupervisorRequest(
                    ManifestHandoffRecoveryClaimId(value["claim_id"]),
                    ManifestHandoffRecoveryOwnerId(value["owner_id"]), binding, name,
                )
            document = ManifestHandoffSupervisorLaunchDocument(
                ManifestHandoffSupervisorControlArtifactId(value["document_id"]),
                ManifestHandoffSupervisorCreationId(value["creation_id"]), gate,
                ManifestHandoffSupervisorImageDigest(value["image_digest"]), request,
            )
            if self.encode(document).content.value != content:
                raise ManifestHandoffRegistryUnavailable
            return document
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ManifestHandoffRegistryUnavailable
        value[key] = item
    return value
