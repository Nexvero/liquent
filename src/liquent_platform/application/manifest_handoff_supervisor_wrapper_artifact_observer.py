"""Observe and persist direct child Ready and Consumed artifacts only."""

from liquent_platform.identity.manifest_handoff_supervisor_control_artifact import (
    ManifestHandoffSupervisorReadyDocument,
    ManifestHandoffSupervisorReleaseConsumedDocument,
    ManifestHandoffSupervisorTerminalEnvelopeDocument,
    PublishedManifestHandoffSupervisorControlArtifact,
    ReadManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.identity.manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorReleaseId,
)
from liquent_platform.identity.manifest_handoff_supervisor_gate_wrapper import (
    StartManifestHandoffSupervisorGateWrapper,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactRole,
    ManifestHandoffSupervisorRuntimeConflict,
    RecordManifestHandoffSupervisorReadyArtifact,
    RecordManifestHandoffSupervisorReleaseConsumedArtifact,
    RecordManifestHandoffSupervisorTerminalEnvelopeArtifact,
    RecordedManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.identity.manifest_handoff_supervisor_terminal_observation import (
    ObservedManifestHandoffSupervisorTerminalArtifact,
    RecordedManifestHandoffSupervisorTerminalArtifact,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


class ReadOnlyManifestHandoffSupervisorWrapperArtifactObserver:
    __slots__ = ("_codec", "_reader")

    def __init__(self, *, reader, codec) -> None:
        if reader is None or codec is None:
            raise ManifestHandoffRegistryUnavailable
        self._reader, self._codec = reader, codec

    def __repr__(self) -> str:
        return "ReadOnlyManifestHandoffSupervisorWrapperArtifactObserver()"

    def observe_ready(self, gate):
        if type(gate) is not StartManifestHandoffSupervisorGateWrapper:
            raise ManifestHandoffRegistryUnavailable
        return self._observe(
            gate, ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY,
            ManifestHandoffSupervisorReadyDocument, gate.ready_artifact_id,
            gate.gated_observation_id,
        )

    def observe_consumed(self, gate, release_id):
        if (type(gate) is not StartManifestHandoffSupervisorGateWrapper
                or type(release_id) is not ManifestHandoffSupervisorReleaseId):
            raise ManifestHandoffRegistryUnavailable
        return self._observe(
            gate, ManifestHandoffSupervisorControlArtifactRole.RELEASE_CONSUMED,
            ManifestHandoffSupervisorReleaseConsumedDocument,
            gate.consumed_artifact_id, release_id,
        )

    def observe_terminal(self, gate):
        if type(gate) is not StartManifestHandoffSupervisorGateWrapper:
            raise ManifestHandoffRegistryUnavailable
        try:
            encoded = self._reader.read(ReadManifestHandoffSupervisorControlArtifact(
                gate.control_directory_id,
                ManifestHandoffSupervisorControlArtifactRole.TERMINAL_ENVELOPE,
            ))
            if encoded is None:
                return None
            document = self._codec.decode(encoded)
            if (type(document) is not ManifestHandoffSupervisorTerminalEnvelopeDocument
                    or document.artifact_id != gate.terminal_artifact_id
                    or document.handle_id != gate.handle_id
                    or document.correlation_id != gate.terminal_observation_id
                    or encoded.artifact_id != gate.terminal_artifact_id
                    or encoded.handle_id != gate.handle_id
                    or encoded.role is not ManifestHandoffSupervisorControlArtifactRole.TERMINAL_ENVELOPE):
                raise ManifestHandoffRegistryUnavailable
            publication = PublishedManifestHandoffSupervisorControlArtifact(
                gate.control_directory_id, gate.terminal_artifact_id,
                ManifestHandoffSupervisorControlArtifactRole.TERMINAL_ENVELOPE,
                encoded.facts,
            )
            return ObservedManifestHandoffSupervisorTerminalArtifact(document, publication)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def _observe(self, gate, role, document_type, artifact_id, correlation_id):
        try:
            encoded = self._reader.read(ReadManifestHandoffSupervisorControlArtifact(
                gate.control_directory_id, role
            ))
            if encoded is None:
                return None
            document = self._codec.decode(encoded)
            if (type(document) is not document_type
                    or document.artifact_id != artifact_id
                    or document.handle_id != gate.handle_id
                    or document.correlation_id != correlation_id
                    or encoded.artifact_id != artifact_id
                    or encoded.handle_id != gate.handle_id
                    or encoded.role is not role):
                raise ManifestHandoffRegistryUnavailable
            return PublishedManifestHandoffSupervisorControlArtifact(
                gate.control_directory_id, artifact_id, role, encoded.facts
            )
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None


class PersistentManifestHandoffSupervisorWrapperArtifactRecorder:
    __slots__ = ("_artifacts", "_observer")

    def __init__(self, *, observer, control_artifacts) -> None:
        if observer is None or control_artifacts is None:
            raise ManifestHandoffRegistryUnavailable
        self._observer, self._artifacts = observer, control_artifacts

    def __repr__(self) -> str:
        return "PersistentManifestHandoffSupervisorWrapperArtifactRecorder()"

    def record_ready(self, gate):
        observed = self._observer.observe_ready(gate)
        if observed is None:
            return None
        try:
            result = self._artifacts.record_ready(
                RecordManifestHandoffSupervisorReadyArtifact(
                    gate.ready_artifact_id, gate.handle_id,
                    gate.gated_observation_id, observed.facts,
                )
            )
            return self._require_record(result, gate,
                ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY,
                gate.ready_artifact_id, gate.gated_observation_id)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def record_consumed(self, gate, release_id):
        observed = self._observer.observe_consumed(gate, release_id)
        if observed is None:
            return None
        try:
            result = self._artifacts.record_release_consumed(
                RecordManifestHandoffSupervisorReleaseConsumedArtifact(
                    gate.consumed_artifact_id, gate.handle_id, release_id, observed.facts,
                )
            )
            return self._require_record(result, gate,
                ManifestHandoffSupervisorControlArtifactRole.RELEASE_CONSUMED,
                gate.consumed_artifact_id, release_id)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def record_terminal(self, gate):
        observed = self._observer.observe_terminal(gate)
        if observed is None:
            return None
        try:
            result = self._artifacts.record_terminal_envelope(
                RecordManifestHandoffSupervisorTerminalEnvelopeArtifact(
                    gate.terminal_artifact_id, gate.handle_id,
                    gate.terminal_observation_id, observed.publication.facts,
                )
            )
            if type(result) is ManifestHandoffSupervisorRuntimeConflict:
                return result
            return RecordedManifestHandoffSupervisorTerminalArtifact(observed, result)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _require_record(result, gate, role, artifact_id, correlation_id):
        if type(result) is ManifestHandoffSupervisorRuntimeConflict:
            return result
        if (type(result) is not RecordedManifestHandoffSupervisorControlArtifact
                or result.handle_id != gate.handle_id or result.role is not role
                or result.artifact_id != artifact_id
                or result.correlation_id != correlation_id):
            raise ManifestHandoffRegistryUnavailable
        return result
