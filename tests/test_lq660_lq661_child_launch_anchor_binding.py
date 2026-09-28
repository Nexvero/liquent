import json

import pytest

from liquent_platform.identity.manifest_handoff_supervisor import (
    ManifestHandoffSupervisorHandleId,
)
from liquent_platform.identity.manifest_handoff_supervisor_engine import (
    ManifestHandoffSupervisorEngineProfile,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_anchor import (
    ManifestHandoffSupervisorLaunchDocumentDigest,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_document import (
    ManifestHandoffSupervisorLaunchDocumentExpectation,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactId,
    ManifestHandoffSupervisorControlDirectoryId,
    ManifestHandoffSupervisorCreationId,
    ManifestHandoffSupervisorImageDigest,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_child_launch_anchor import (
    CanonicalManifestHandoffSupervisorChildLaunchAnchorCodec,
)


def expectation():
    return ManifestHandoffSupervisorLaunchDocumentExpectation(
        ManifestHandoffSupervisorControlArtifactId("document-660"),
        ManifestHandoffSupervisorLaunchDocumentDigest("a" * 64),
        ManifestHandoffSupervisorCreationId("creation-660"),
        ManifestHandoffSupervisorHandleId("handle-660"),
        ManifestHandoffSupervisorControlDirectoryId("directory-660"),
        ManifestHandoffSupervisorImageDigest("sha256:" + "b" * 64),
        ManifestHandoffSupervisorEngineProfile.WRITER,
    )


def test_fixed_arguments_round_trip_every_external_expectation_fact():
    codec = CanonicalManifestHandoffSupervisorChildLaunchAnchorCodec()
    encoded = codec.encode(expectation())
    assert len(encoded) == 14
    assert codec.decode(encoded) == expectation()
    assert "allow" not in " ".join(encoded).lower()
    assert "role" not in " ".join(encoded).lower()


@pytest.mark.parametrize("mutation", [
    lambda value: value[:-2],
    lambda value: ("--caller-override",) + value[1:],
    lambda value: value + ("--extra", "true"),
    lambda value: value[:3] + ("other",) + value[4:],
])
def test_missing_reordered_extra_or_divergent_arguments_fail_closed(mutation):
    codec = CanonicalManifestHandoffSupervisorChildLaunchAnchorCodec()
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        codec.decode(mutation(codec.encode(expectation())))
    assert str(caught.value) == "manifest_handoff_registry_unavailable"


def test_arguments_are_not_json_environment_or_caller_authority():
    encoded = CanonicalManifestHandoffSupervisorChildLaunchAnchorCodec().encode(
        expectation()
    )
    with pytest.raises((TypeError, json.JSONDecodeError)):
        json.loads(encoded)
    assert all("=" not in item for item in encoded[::2])
