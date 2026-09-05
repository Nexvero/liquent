import hashlib
import json
from pathlib import Path

import pytest

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
    ManifestHandoffSupervisorLaunchDocument,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactId,
    ManifestHandoffSupervisorControlDirectoryId,
    ManifestHandoffSupervisorCreationId,
    ManifestHandoffSupervisorImageDigest,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_launch_document import (
    CanonicalManifestHandoffSupervisorLaunchDocumentCodec,
)


def launch(profile=ManifestHandoffSupervisorEngineProfile.WRITER):
    gate = StartManifestHandoffSupervisorGateWrapper(
        ManifestHandoffSupervisorHandleId("handle-608"),
        ManifestHandoffSupervisorControlDirectoryId("directory-608"), profile,
        ManifestHandoffSupervisorControlArtifactId("ready-608"),
        ManifestHandoffSupervisorGatedObservationId("gated-608"),
        ManifestHandoffSupervisorControlArtifactId("consumed-608"),
        ManifestHandoffSupervisorControlArtifactId("terminal-608"),
        ManifestHandoffSupervisorTerminalObservationId("terminal-observation-608"),
    )
    binding = ManifestHandoffScopeBinding(
        ManifestHandoffRegistryScopeId("scope-608"), Path("/srv/source"), Path("/srv/target")
    )
    if profile is ManifestHandoffSupervisorEngineProfile.WRITER:
        request = ManifestHandoffWriterSupervisorRequest(
            ManifestHandoffExecutionClaimId("claim-608"),
            ManifestHandoffExecutionOwnerId("owner-608"), binding,
            ManifestHandoffName("handoff-608"),
        )
    else:
        request = ManifestHandoffRecoverySupervisorRequest(
            ManifestHandoffRecoveryClaimId("claim-608"),
            ManifestHandoffRecoveryOwnerId("owner-608"), binding,
            ManifestHandoffName("handoff-608"),
        )
    return ManifestHandoffSupervisorLaunchDocument(
        ManifestHandoffSupervisorControlArtifactId("launch-608"),
        ManifestHandoffSupervisorCreationId("creation-608"), gate,
        ManifestHandoffSupervisorImageDigest("sha256:" + "d" * 64), request,
    )


@pytest.mark.parametrize("profile", list(ManifestHandoffSupervisorEngineProfile))
def test_both_profiles_round_trip_with_precreate_facts(profile):
    codec = CanonicalManifestHandoffSupervisorLaunchDocumentCodec()
    document = launch(profile)
    encoded = codec.encode(document)
    assert codec.decode(encoded) == document
    assert codec.decode_content(encoded.content.value) == document
    payload = json.loads(encoded.content.value)
    assert list(payload) == sorted(payload)
    assert payload["creation_id"] == "creation-608"
    assert payload["profile"] == profile.value
    assert "runtime_container_id" not in payload
    assert encoded.facts.sha256 == hashlib.sha256(encoded.content.value).hexdigest()


def test_cross_profile_request_is_rejected():
    writer, recovery = launch(), launch(ManifestHandoffSupervisorEngineProfile.RECOVERY)
    with pytest.raises(ValueError):
        ManifestHandoffSupervisorLaunchDocument(
            writer.document_id, writer.creation_id, writer.gate,
            writer.image_digest, recovery.request,
        )


@pytest.mark.parametrize("mutation", [
    lambda value: value.update(runtime_container_id="a" * 64),
    lambda value: value.update(version=2),
    lambda value: value.update(profile="cleanup"),
    lambda value: value.update(source_root="relative"),
    lambda value: value.update(creation_id=""),
    lambda value: value.update(ready_artifact_id=value["consumed_artifact_id"]),
])
def test_unknown_or_divergent_values_fail_closed(mutation):
    codec = CanonicalManifestHandoffSupervisorLaunchDocumentCodec()
    value = json.loads(codec.encode(launch()).content.value)
    mutation(value)
    content = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        codec.decode_content(content)


def test_duplicate_keys_noncanonical_bytes_and_oversize_fail_closed():
    codec = CanonicalManifestHandoffSupervisorLaunchDocumentCodec()
    content = codec.encode(launch()).content.value
    for invalid in (
        content[:-1] + b',"version":1}',
        content.replace(b'":', b'": '),
        b"x" * 65_537,
        b"",
    ):
        with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
            codec.decode_content(invalid)
        assert "creation-608" not in str(caught.value)


def test_digest_changes_for_every_independent_anchor_dimension():
    codec = CanonicalManifestHandoffSupervisorLaunchDocumentCodec()
    original = json.loads(codec.encode(launch()).content.value)
    digests = set()
    for key, replacement in (
        ("document_id", "launch-other"),
        ("creation_id", "creation-other"),
        ("handle_id", "handle-other"),
        ("control_directory_id", "directory-other"),
        ("image_digest", "sha256:" + "e" * 64),
        ("claim_id", "claim-other"),
        ("owner_id", "owner-other"),
        ("scope_id", "scope-other"),
    ):
        value = dict(original)
        value[key] = replacement
        raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        digests.add(hashlib.sha256(raw).hexdigest())
    assert len(digests) == 8
    assert hashlib.sha256(codec.encode(launch()).content.value).hexdigest() not in digests


def test_codec_repr_discloses_no_configuration():
    assert repr(CanonicalManifestHandoffSupervisorLaunchDocumentCodec()) == (
        "CanonicalManifestHandoffSupervisorLaunchDocumentCodec()"
    )
