"""Canonical fixed arguments for one externally anchored supervisor child."""

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


_FLAGS = (
    "--liquent-launch-document", "--liquent-launch-sha256",
    "--liquent-creation", "--liquent-handle", "--liquent-control-directory",
    "--liquent-image-digest", "--liquent-profile",
)


class CanonicalManifestHandoffSupervisorChildLaunchAnchorCodec:
    """Encode and decode only the fixed ordered child launch anchor arguments."""

    __slots__ = ()

    def encode(self, expectation) -> tuple[str, ...]:
        if type(expectation) is not ManifestHandoffSupervisorLaunchDocumentExpectation:
            raise ManifestHandoffRegistryUnavailable
        values = (
            expectation.document_id.value, expectation.digest.value,
            expectation.creation_id.value, expectation.handle_id.value,
            expectation.control_directory_id.value, expectation.image_digest.value,
            expectation.profile.value,
        )
        if not all(_safe(value) for value in values):
            raise ManifestHandoffRegistryUnavailable
        return tuple(item for pair in zip(_FLAGS, values, strict=True) for item in pair)

    def decode(self, arguments) -> ManifestHandoffSupervisorLaunchDocumentExpectation:
        if (type(arguments) is not tuple or len(arguments) != len(_FLAGS) * 2
                or tuple(arguments[::2]) != _FLAGS
                or not all(_safe(value) for value in arguments[1::2])):
            raise ManifestHandoffRegistryUnavailable
        values = arguments[1::2]
        try:
            return ManifestHandoffSupervisorLaunchDocumentExpectation(
                ManifestHandoffSupervisorControlArtifactId(values[0]),
                ManifestHandoffSupervisorLaunchDocumentDigest(values[1]),
                ManifestHandoffSupervisorCreationId(values[2]),
                ManifestHandoffSupervisorHandleId(values[3]),
                ManifestHandoffSupervisorControlDirectoryId(values[4]),
                ManifestHandoffSupervisorImageDigest(values[5]),
                ManifestHandoffSupervisorEngineProfile(values[6]),
            )
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None


def _safe(value: object) -> bool:
    return (
        type(value) is str and 0 < len(value) <= 512
        and "\x00" not in value and "\n" not in value and "\r" not in value
    )
