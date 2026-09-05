import json
import os
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
from liquent_platform.identity.manifest_handoff_supervisor_job_document import (
    ManifestHandoffSupervisorJobDocument,
    ManifestHandoffSupervisorJobDocumentConflict,
    PublishManifestHandoffSupervisorJobDocument,
)
from liquent_platform.identity.manifest_handoff_supervisor_journal import (
    ManifestHandoffSupervisorGatedObservationId,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactId,
    ManifestHandoffSupervisorControlDirectoryId,
    ManifestHandoffSupervisorImageDigest,
    ManifestHandoffSupervisorRuntimeContainerId,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_job_document import (
    AtomicLocalManifestHandoffSupervisorJobDocuments,
    CanonicalManifestHandoffSupervisorJobDocumentCodec,
)


def job(profile=ManifestHandoffSupervisorEngineProfile.WRITER, *, document_id="job-600"):
    gate = StartManifestHandoffSupervisorGateWrapper(
        ManifestHandoffSupervisorHandleId("handle-600"),
        ManifestHandoffSupervisorControlDirectoryId("directory-600"),
        profile,
        ManifestHandoffSupervisorControlArtifactId("ready-600"),
        ManifestHandoffSupervisorGatedObservationId("gated-600"),
        ManifestHandoffSupervisorControlArtifactId("consumed-600"),
        ManifestHandoffSupervisorControlArtifactId("terminal-600"),
        ManifestHandoffSupervisorTerminalObservationId("terminal-observation-600"),
    )
    binding = ManifestHandoffScopeBinding(
        ManifestHandoffRegistryScopeId("scope-600"),
        Path("/srv/liquent/source"), Path("/srv/liquent/target"),
    )
    if profile is ManifestHandoffSupervisorEngineProfile.WRITER:
        request = ManifestHandoffWriterSupervisorRequest(
            ManifestHandoffExecutionClaimId("claim-600"),
            ManifestHandoffExecutionOwnerId("owner-600"), binding,
            ManifestHandoffName("handoff-600"),
        )
    else:
        request = ManifestHandoffRecoverySupervisorRequest(
            ManifestHandoffRecoveryClaimId("claim-600"),
            ManifestHandoffRecoveryOwnerId("owner-600"), binding,
            ManifestHandoffName("handoff-600"),
        )
    return ManifestHandoffSupervisorJobDocument(
        ManifestHandoffSupervisorControlArtifactId(document_id), gate,
        ManifestHandoffSupervisorRuntimeContainerId("a" * 64),
        ManifestHandoffSupervisorImageDigest("sha256:" + "b" * 64), request,
    )


@pytest.mark.parametrize("profile", list(ManifestHandoffSupervisorEngineProfile))
def test_canonical_job_document_round_trips_both_profiles(profile):
    codec = CanonicalManifestHandoffSupervisorJobDocumentCodec()
    value = job(profile)
    encoded = codec.encode(value)
    assert codec.decode(encoded) == value
    assert codec.decode_content(encoded.content.value) == value
    payload = json.loads(encoded.content.value)
    assert list(payload) == sorted(payload)
    assert payload["profile"] == profile.value
    assert payload["runtime_container_id"] == "a" * 64
    assert payload["image_digest"] == "sha256:" + "b" * 64
    assert payload["source_root"] == "/srv/liquent/source"
    assert payload["target_root"] == "/srv/liquent/target"


def test_profile_and_request_kind_cannot_cross():
    writer = job()
    recovery = job(ManifestHandoffSupervisorEngineProfile.RECOVERY)
    with pytest.raises(ValueError):
        ManifestHandoffSupervisorJobDocument(
            writer.document_id, writer.gate, writer.runtime_container_id,
            writer.image_digest, recovery.request,
        )


@pytest.mark.parametrize("mutation", [
    lambda value: value.update(extra=True),
    lambda value: value.update(version=2),
    lambda value: value.update(profile="cleanup"),
    lambda value: value.update(source_root="relative"),
    lambda value: value.update(ready_artifact_id=value["consumed_artifact_id"]),
])
def test_decode_rejects_unknown_or_divergent_binding(mutation):
    codec = CanonicalManifestHandoffSupervisorJobDocumentCodec()
    payload = json.loads(codec.encode(job()).content.value)
    mutation(payload)
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        codec.decode_content(raw)


def test_decode_rejects_duplicate_keys_and_noncanonical_bytes():
    codec = CanonicalManifestHandoffSupervisorJobDocumentCodec()
    raw = codec.encode(job()).content.value
    duplicate = raw[:-1] + b',"version":1}'
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        codec.decode_content(duplicate)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        codec.decode_content(raw.replace(b'":', b'": '))


def store(tmp_path):
    root = tmp_path / "control"
    directory = root / "job"
    root.mkdir(mode=0o700)
    directory.mkdir(mode=0o700)
    codec = CanonicalManifestHandoffSupervisorJobDocumentCodec()
    adapter = AtomicLocalManifestHandoffSupervisorJobDocuments(
        root,
        resolve_directory=lambda value: directory if value.value == "directory-600" else None,
        codec=codec,
    )
    return adapter, codec, directory


def test_atomic_publish_read_and_identical_retry(tmp_path):
    adapter, codec, directory = store(tmp_path)
    encoded = codec.encode(job())
    request = PublishManifestHandoffSupervisorJobDocument(encoded)
    first = adapter.publish(request)
    second = adapter.publish(request)
    assert first == second
    assert adapter.read(job().gate.control_directory_id) == job()
    path = directory / "job-binding.json"
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.stat().st_nlink == 1
    assert not list(directory.glob(".pending-job-*"))


def test_divergent_retry_is_conflict_and_preserves_original(tmp_path):
    adapter, codec, directory = store(tmp_path)
    original = codec.encode(job())
    adapter.publish(PublishManifestHandoffSupervisorJobDocument(original))
    before = (directory / "job-binding.json").read_bytes()
    result = adapter.publish(PublishManifestHandoffSupervisorJobDocument(
        codec.encode(job(document_id="job-other"))
    ))
    assert type(result) is ManifestHandoffSupervisorJobDocumentConflict
    assert (directory / "job-binding.json").read_bytes() == before


def test_absence_is_neutral_but_unsafe_file_is_unavailable(tmp_path):
    adapter, _, directory = store(tmp_path)
    directory_id = job().gate.control_directory_id
    assert adapter.read(directory_id) is None
    path = directory / "job-binding.json"
    path.write_bytes(b"{}")
    os.chmod(path, 0o644)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        adapter.read(directory_id)


def test_repr_and_errors_disclose_no_binding_values(tmp_path):
    adapter, codec, _ = store(tmp_path)
    assert repr(adapter) == "AtomicLocalManifestHandoffSupervisorJobDocuments()"
    encoded = codec.encode(job())
    assert "handle-600" not in repr(encoded)
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        adapter.read(ManifestHandoffSupervisorControlDirectoryId("unknown"))
    assert "unknown" not in str(caught.value)
