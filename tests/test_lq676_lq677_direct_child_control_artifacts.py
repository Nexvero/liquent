import os
from pathlib import Path

import pytest

from liquent_platform.identity.manifest_handoff_supervisor import (
    ManifestHandoffSupervisorHandleId,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_artifact import (
    ManifestHandoffSupervisorControlArtifactConflict,
    ManifestHandoffSupervisorReadyDocument,
    PublishManifestHandoffSupervisorControlArtifact,
    ReadManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.identity.manifest_handoff_supervisor_journal import (
    ManifestHandoffSupervisorGatedObservationId,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactId,
    ManifestHandoffSupervisorControlArtifactRole,
    ManifestHandoffSupervisorControlDirectoryId,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_control_artifacts import (
    CanonicalManifestHandoffSupervisorControlArtifactCodec,
    DirectAtomicLocalManifestHandoffSupervisorControlArtifacts,
)


DIRECTORY_ID = ManifestHandoffSupervisorControlDirectoryId("directory-676")


def setup(tmp_path: Path):
    parent = tmp_path / "run-liquent"
    parent.mkdir(mode=0o755)
    directory = parent / "control"
    directory.mkdir(mode=0o700)
    codec = CanonicalManifestHandoffSupervisorControlArtifactCodec()
    adapter = DirectAtomicLocalManifestHandoffSupervisorControlArtifacts(
        directory, control_directory_id=DIRECTORY_ID, codec=codec
    )
    document = ManifestHandoffSupervisorReadyDocument(
        ManifestHandoffSupervisorControlArtifactId("ready-676"),
        ManifestHandoffSupervisorHandleId("handle-676"),
        ManifestHandoffSupervisorGatedObservationId("gated-676"),
    )
    return directory, codec, adapter, document


def test_direct_adapter_publishes_and_reads_same_canonical_artifact(tmp_path):
    directory, codec, adapter, document = setup(tmp_path)
    artifact = codec.encode(document)
    published = adapter.publish(
        PublishManifestHandoffSupervisorControlArtifact(DIRECTORY_ID, artifact)
    )
    observed = adapter.read(ReadManifestHandoffSupervisorControlArtifact(
        DIRECTORY_ID, ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY
    ))
    assert observed == artifact
    assert published.facts == artifact.facts
    assert (directory / "wrapper-ready.json").read_bytes() == artifact.content.value
    assert not list(directory.glob(".pending-*"))


def test_identical_retry_is_effect_free_and_divergence_is_conflict(tmp_path):
    directory, codec, adapter, document = setup(tmp_path)
    request = PublishManifestHandoffSupervisorControlArtifact(
        DIRECTORY_ID, codec.encode(document)
    )
    first = adapter.publish(request)
    facts = (directory / "wrapper-ready.json").stat()
    assert adapter.publish(request) == first
    after = (directory / "wrapper-ready.json").stat()
    assert (facts.st_ino, facts.st_mtime_ns) == (after.st_ino, after.st_mtime_ns)
    other = ManifestHandoffSupervisorReadyDocument(
        document.artifact_id, ManifestHandoffSupervisorHandleId("other-handle"),
        document.correlation_id,
    )
    result = adapter.publish(PublishManifestHandoffSupervisorControlArtifact(
        DIRECTORY_ID, codec.encode(other)
    ))
    assert type(result) is ManifestHandoffSupervisorControlArtifactConflict


def test_absence_is_neutral_but_wrong_directory_id_fails_before_open(tmp_path):
    directory, _, adapter, _ = setup(tmp_path)
    role = ManifestHandoffSupervisorControlArtifactRole.RELEASE_TOKEN
    assert adapter.read(ReadManifestHandoffSupervisorControlArtifact(
        DIRECTORY_ID, role
    )) is None
    wrong = ManifestHandoffSupervisorControlDirectoryId("other-directory")
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        adapter.read(ReadManifestHandoffSupervisorControlArtifact(wrong, role))
    assert list(directory.iterdir()) == []


def test_direct_directory_is_no_follow_private_and_current_user_owned(tmp_path):
    directory, codec, _, _ = setup(tmp_path)
    directory.chmod(0o755)
    adapter = DirectAtomicLocalManifestHandoffSupervisorControlArtifacts(
        directory, control_directory_id=DIRECTORY_ID, codec=codec
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        adapter.read(ReadManifestHandoffSupervisorControlArtifact(
            DIRECTORY_ID, ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY
        ))
    directory.chmod(0o700)
    outside = tmp_path / "outside"
    outside.mkdir(mode=0o700)
    directory.rmdir()
    directory.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        adapter.read(ReadManifestHandoffSupervisorControlArtifact(
            DIRECTORY_ID, ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY
        ))


def test_parent_mode_is_not_misclassified_as_child_directory_policy(tmp_path):
    directory, _, adapter, _ = setup(tmp_path)
    assert (directory.parent.stat().st_mode & 0o777) == 0o755
    assert directory.stat().st_uid == os.geteuid()
    assert adapter.read(ReadManifestHandoffSupervisorControlArtifact(
        DIRECTORY_ID, ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY
    )) is None


def test_repr_and_surface_disclose_no_path_id_or_cleanup_power(tmp_path):
    _, _, adapter, _ = setup(tmp_path)
    representation = repr(adapter)
    assert representation == "DirectAtomicLocalManifestHandoffSupervisorControlArtifacts()"
    assert "676" not in representation and str(tmp_path) not in representation
    for forbidden in ("remove", "delete", "cleanup", "overwrite"):
        assert not hasattr(adapter, forbidden)
