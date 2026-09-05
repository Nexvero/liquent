import os
from pathlib import Path

import pytest

from liquent_platform.identity.manifest_handoff_supervisor import (
    ManifestHandoffSupervisorHandleId,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_anchor import (
    ManifestHandoffSupervisorLaunchDocumentDigest,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_document import (
    ManifestHandoffSupervisorLaunchDocumentExpectation,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_identity import (
    ManifestHandoffSupervisorLaunchIdentityPolicy,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactId,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_launch_document import (
    CanonicalManifestHandoffSupervisorLaunchDocumentCodec,
)
from liquent_platform.transport.manifest_handoff_supervisor_launch_loader import (
    ReadOnlyManifestHandoffSupervisorLaunchDocumentLoader,
)
from test_lq612_lq613_supervisor_launch_file import document


def policy():
    return ManifestHandoffSupervisorLaunchIdentityPolicy(
        os.geteuid(), os.getegid(), os.geteuid() + 1, os.getegid()
    )


def setup_loader(tmp_path: Path):
    root = tmp_path / "launch"
    root.mkdir(mode=0o700)
    codec = CanonicalManifestHandoffSupervisorLaunchDocumentCodec()
    encoded = codec.encode(document())
    launch = root / "launch-binding.json"
    launch.write_bytes(encoded.content.value)
    launch.chmod(0o640)
    expectation = ManifestHandoffSupervisorLaunchDocumentExpectation(
        document().document_id,
        ManifestHandoffSupervisorLaunchDocumentDigest(encoded.facts.sha256),
        document().creation_id, document().gate.handle_id,
        document().gate.control_directory_id, document().image_digest,
        document().gate.profile,
    )
    return ReadOnlyManifestHandoffSupervisorLaunchDocumentLoader(
        root, codec=codec, identity_policy=policy()
    ), expectation, launch


def test_loader_accepts_exact_external_anchor_and_self_binding(tmp_path):
    loader, expectation, _ = setup_loader(tmp_path)
    assert loader.load(expectation) == document()
    assert repr(loader) == "ReadOnlyManifestHandoffSupervisorLaunchDocumentLoader()"


def test_loader_rejects_divergent_digest_and_document_id_detail_free(tmp_path):
    loader, expectation, _ = setup_loader(tmp_path)
    divergent = (
        ManifestHandoffSupervisorLaunchDocumentExpectation(
            expectation.document_id, ManifestHandoffSupervisorLaunchDocumentDigest("e" * 64),
            expectation.creation_id, expectation.handle_id,
            expectation.control_directory_id, expectation.image_digest, expectation.profile,
        ),
        ManifestHandoffSupervisorLaunchDocumentExpectation(
            ManifestHandoffSupervisorControlArtifactId("other"), expectation.digest,
            expectation.creation_id, expectation.handle_id,
            expectation.control_directory_id, expectation.image_digest, expectation.profile,
        ),
        ManifestHandoffSupervisorLaunchDocumentExpectation(
            expectation.document_id, expectation.digest, expectation.creation_id,
            ManifestHandoffSupervisorHandleId("other"), expectation.control_directory_id,
            expectation.image_digest, expectation.profile,
        ),
    )
    for value in divergent:
        with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
            loader.load(value)
        assert str(caught.value) == "manifest_handoff_registry_unavailable"


@pytest.mark.parametrize("mode", [0o600, 0o644, 0o660])
def test_loader_rejects_non_reader_bound_modes(tmp_path, mode):
    loader, expectation, launch = setup_loader(tmp_path)
    launch.chmod(mode)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        loader.load(expectation)


def test_loader_rejects_symlink_and_hardlink(tmp_path):
    loader, expectation, launch = setup_loader(tmp_path)
    content = launch.read_bytes()
    launch.unlink()
    outside = tmp_path / "outside"
    outside.write_bytes(content)
    outside.chmod(0o640)
    launch.symlink_to(outside)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        loader.load(expectation)
    launch.unlink()
    os.link(outside, launch)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        loader.load(expectation)
