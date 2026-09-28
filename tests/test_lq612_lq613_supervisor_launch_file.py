import os
from pathlib import Path

import pytest

from liquent_platform.identity.manifest_handoff import (
    ManifestHandoffExecutionClaimId, ManifestHandoffExecutionOwnerId,
    ManifestHandoffName, ManifestHandoffRegistryScopeId, ManifestHandoffScopeBinding,
)
from liquent_platform.identity.manifest_handoff_supervisor import (
    ManifestHandoffSupervisorHandleId, ManifestHandoffWriterSupervisorRequest,
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
    ManifestHandoffSupervisorLaunchDocumentConflict,
    PublishManifestHandoffSupervisorLaunchDocument,
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
from liquent_platform.transport.manifest_handoff_supervisor_launch_file import (
    AtomicLocalManifestHandoffSupervisorLaunchDocuments,
)


def document(document_id="launch-612"):
    gate = StartManifestHandoffSupervisorGateWrapper(
        ManifestHandoffSupervisorHandleId("handle-612"),
        ManifestHandoffSupervisorControlDirectoryId("directory-612"),
        ManifestHandoffSupervisorEngineProfile.WRITER,
        ManifestHandoffSupervisorControlArtifactId("ready-612"),
        ManifestHandoffSupervisorGatedObservationId("gated-612"),
        ManifestHandoffSupervisorControlArtifactId("consumed-612"),
        ManifestHandoffSupervisorControlArtifactId("terminal-612"),
        ManifestHandoffSupervisorTerminalObservationId("terminal-observation-612"),
    )
    request = ManifestHandoffWriterSupervisorRequest(
        ManifestHandoffExecutionClaimId("claim-612"),
        ManifestHandoffExecutionOwnerId("owner-612"),
        ManifestHandoffScopeBinding(
            ManifestHandoffRegistryScopeId("scope-612"),
            Path("/srv/source"), Path("/srv/target"),
        ),
        ManifestHandoffName("handoff-612"),
    )
    return ManifestHandoffSupervisorLaunchDocument(
        ManifestHandoffSupervisorControlArtifactId(document_id),
        ManifestHandoffSupervisorCreationId("creation-612"), gate,
        ManifestHandoffSupervisorImageDigest("sha256:" + "f" * 64), request,
    )


def setup_store(tmp_path):
    root, directory = tmp_path / "control", tmp_path / "control" / "job"
    root.mkdir(mode=0o700)
    directory.mkdir(mode=0o700)
    codec = CanonicalManifestHandoffSupervisorLaunchDocumentCodec()
    store = AtomicLocalManifestHandoffSupervisorLaunchDocuments(
        root,
        resolve_directory=lambda value: directory if value.value == "directory-612" else None,
        codec=codec,
    )
    return store, codec, directory


def test_publish_is_private_atomic_and_readable(tmp_path):
    store, codec, directory = setup_store(tmp_path)
    encoded = codec.encode(document())
    result = store.publish(PublishManifestHandoffSupervisorLaunchDocument(encoded))
    path = directory / "launch-binding.json"
    assert result.document_id == document().document_id
    assert result.facts == encoded.facts
    assert path.read_bytes() == encoded.content.value
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.stat().st_nlink == 1
    assert store.read(document().gate.control_directory_id) == document()
    assert not list(directory.glob(".pending-launch-*"))


def test_identical_retry_is_stable_without_rewrite(tmp_path):
    store, codec, directory = setup_store(tmp_path)
    request = PublishManifestHandoffSupervisorLaunchDocument(codec.encode(document()))
    first = store.publish(request)
    facts = (directory / "launch-binding.json").stat()
    second = store.publish(request)
    after = (directory / "launch-binding.json").stat()
    assert first == second
    assert (facts.st_ino, facts.st_mtime_ns) == (after.st_ino, after.st_mtime_ns)


def test_divergent_retry_is_effect_free_conflict(tmp_path):
    store, codec, directory = setup_store(tmp_path)
    store.publish(PublishManifestHandoffSupervisorLaunchDocument(codec.encode(document())))
    path = directory / "launch-binding.json"
    before = path.read_bytes()
    result = store.publish(PublishManifestHandoffSupervisorLaunchDocument(
        codec.encode(document("launch-other"))
    ))
    assert type(result) is ManifestHandoffSupervisorLaunchDocumentConflict
    assert path.read_bytes() == before


def test_absence_is_neutral_and_unknown_directory_is_unavailable(tmp_path):
    store, _, _ = setup_store(tmp_path)
    assert store.read(document().gate.control_directory_id) is None
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        store.read(ManifestHandoffSupervisorControlDirectoryId("unknown"))
    assert "unknown" not in str(caught.value)


@pytest.mark.parametrize("mode", [0o644, 0o400, 0o666])
def test_unsafe_file_mode_is_unavailable(tmp_path, mode):
    store, codec, directory = setup_store(tmp_path)
    path = directory / "launch-binding.json"
    path.write_bytes(codec.encode(document()).content.value)
    os.chmod(path, mode)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        store.read(document().gate.control_directory_id)


def test_symlink_and_hardlink_are_rejected(tmp_path):
    store, codec, directory = setup_store(tmp_path)
    outside = tmp_path / "outside"
    outside.write_bytes(codec.encode(document()).content.value)
    path = directory / "launch-binding.json"
    path.symlink_to(outside)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        store.read(document().gate.control_directory_id)
    path.unlink()
    os.link(outside, path)
    os.chmod(path, 0o600)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        store.read(document().gate.control_directory_id)


def test_repr_and_surface_expose_no_cleanup_or_overwrite(tmp_path):
    store, _, _ = setup_store(tmp_path)
    assert repr(store) == "AtomicLocalManifestHandoffSupervisorLaunchDocuments()"
    assert not any(hasattr(store, name) for name in ("delete", "remove", "replace", "cleanup"))
