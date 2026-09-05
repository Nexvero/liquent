"""Gate wrapper mechanics over closed control-artifact boundaries."""

from liquent_platform.identity.manifest_handoff_supervisor_control_artifact import (
    ManifestHandoffSupervisorControlArtifactConflict,
    ManifestHandoffSupervisorReadyDocument,
    ManifestHandoffSupervisorReleaseConsumedDocument,
    ManifestHandoffSupervisorReleaseTokenDocument,
    ManifestHandoffSupervisorTerminalEnvelopeDocument,
    PublishManifestHandoffSupervisorControlArtifact,
    ReadManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.identity.manifest_handoff_supervisor_gate_wrapper import (
    AcceptedManifestHandoffSupervisorReleaseToken,
    CompleteManifestHandoffSupervisorGateWrapper,
    CompletedManifestHandoffSupervisorGateWrapper,
    ManifestHandoffSupervisorGateWrapperConflict,
    ReadyManifestHandoffSupervisorGateWrapper,
    ReleasedManifestHandoffSupervisorGateWrapper,
    StartManifestHandoffSupervisorGateWrapper,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactRole,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


class FileManifestHandoffSupervisorGateWrapper:
    """Publish and observe only the four closed gate artifact roles."""

    __slots__ = ("_codec", "_publisher", "_reader")

    def __init__(self, *, codec, publisher, reader) -> None:
        if codec is None or publisher is None or reader is None:
            raise ManifestHandoffRegistryUnavailable
        self._codec = codec
        self._publisher = publisher
        self._reader = reader

    def __repr__(self) -> str:
        return "FileManifestHandoffSupervisorGateWrapper()"

    def publish_ready(self, request):
        if type(request) is not StartManifestHandoffSupervisorGateWrapper:
            raise ManifestHandoffRegistryUnavailable
        document = ManifestHandoffSupervisorReadyDocument(
            request.ready_artifact_id, request.handle_id, request.gated_observation_id)
        publication = self._publish(request.control_directory_id, document)
        if type(publication) is ManifestHandoffSupervisorGateWrapperConflict:
            return publication
        try:
            return ReadyManifestHandoffSupervisorGateWrapper(request, publication)
        except (TypeError, ValueError):
            raise ManifestHandoffRegistryUnavailable from None

    def await_release(self, ready):
        if type(ready) is not ReadyManifestHandoffSupervisorGateWrapper:
            raise ManifestHandoffRegistryUnavailable
        binding = ready.binding
        try:
            artifact = self._reader.read(ReadManifestHandoffSupervisorControlArtifact(
                binding.control_directory_id,
                ManifestHandoffSupervisorControlArtifactRole.RELEASE_TOKEN))
            if artifact is None:
                return None
            document = self._codec.decode(artifact)
            if (type(document) is not ManifestHandoffSupervisorReleaseTokenDocument
                    or document.handle_id != binding.handle_id):
                raise ManifestHandoffRegistryUnavailable
            return AcceptedManifestHandoffSupervisorReleaseToken(
                ready, document.artifact_id, document.correlation_id)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def publish_consumed(self, token):
        if type(token) is not AcceptedManifestHandoffSupervisorReleaseToken:
            raise ManifestHandoffRegistryUnavailable
        binding = token.ready.binding
        document = ManifestHandoffSupervisorReleaseConsumedDocument(
            binding.consumed_artifact_id, binding.handle_id, token.release_id)
        publication = self._publish(binding.control_directory_id, document)
        if type(publication) is ManifestHandoffSupervisorGateWrapperConflict:
            return publication
        try:
            return ReleasedManifestHandoffSupervisorGateWrapper(token, publication)
        except (TypeError, ValueError):
            raise ManifestHandoffRegistryUnavailable from None

    def publish_terminal(self, request):
        if type(request) is not CompleteManifestHandoffSupervisorGateWrapper:
            raise ManifestHandoffRegistryUnavailable
        gate = request.gate
        if type(gate) is ReadyManifestHandoffSupervisorGateWrapper:
            binding = gate.binding
        elif type(gate) is ReleasedManifestHandoffSupervisorGateWrapper:
            binding = gate.token.ready.binding
        else:
            raise ManifestHandoffRegistryUnavailable
        document = ManifestHandoffSupervisorTerminalEnvelopeDocument(
            binding.terminal_artifact_id, binding.handle_id,
            binding.terminal_observation_id, request.outcome)
        publication = self._publish(binding.control_directory_id, document)
        if type(publication) is ManifestHandoffSupervisorGateWrapperConflict:
            return publication
        try:
            return CompletedManifestHandoffSupervisorGateWrapper(request, publication)
        except (TypeError, ValueError):
            raise ManifestHandoffRegistryUnavailable from None

    def _publish(self, control_directory_id, document):
        try:
            artifact = self._codec.encode(document)
            result = self._publisher.publish(PublishManifestHandoffSupervisorControlArtifact(
                control_directory_id, artifact))
            if type(result) is ManifestHandoffSupervisorControlArtifactConflict:
                return ManifestHandoffSupervisorGateWrapperConflict()
            return result
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
