from datetime import datetime, timezone
from pathlib import Path

import pytest

from liquent_platform.application.manifest_handoff_supervisor_wrapper_artifact_observer import (
    PersistentManifestHandoffSupervisorWrapperArtifactRecorder,
    ReadOnlyManifestHandoffSupervisorWrapperArtifactObserver,
)
from liquent_platform.identity.manifest_handoff_supervisor import (
    CompletedManifestHandoffWriterProcess,
    ManifestHandoffSupervisorHandleId,
    ManifestHandoffWriterProcessKind,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_artifact import (
    ManifestHandoffSupervisorReadyDocument,
    ManifestHandoffSupervisorReleaseConsumedDocument,
    ManifestHandoffSupervisorTerminalEnvelopeDocument,
)
from liquent_platform.identity.manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorReleaseId,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactRole,
    ManifestHandoffSupervisorRuntimeConflict,
    RecordedManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_control_artifacts import (
    CanonicalManifestHandoffSupervisorControlArtifactCodec,
)
from test_lq608_lq609_supervisor_launch_document import launch


NOW = datetime(2026, 8, 28, 12, tzinfo=timezone.utc)
RELEASE = ManifestHandoffSupervisorReleaseId("release-636")


class Reader:
    def __init__(self, values):
        self.values = values
        self.requests = []

    def read(self, request):
        self.requests.append(request)
        return self.values.get(request.role)


class Artifacts:
    def __init__(self, conflict=False):
        self.requests = []
        self.conflict = conflict

    def record_ready(self, request):
        return self._record(request, ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY)

    def record_release_consumed(self, request):
        return self._record(
            request, ManifestHandoffSupervisorControlArtifactRole.RELEASE_CONSUMED
        )

    def record_terminal_envelope(self, request):
        return self._record(
            request, ManifestHandoffSupervisorControlArtifactRole.TERMINAL_ENVELOPE
        )

    def _record(self, request, role):
        self.requests.append(request)
        if self.conflict:
            return ManifestHandoffSupervisorRuntimeConflict()
        return RecordedManifestHandoffSupervisorControlArtifact(
            request.artifact_id, request.handle_id, role,
            request.correlation_id, request.facts, NOW,
        )


def encoded_values(gate):
    codec = CanonicalManifestHandoffSupervisorControlArtifactCodec()
    return codec, {
        ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY: codec.encode(
            ManifestHandoffSupervisorReadyDocument(
                gate.ready_artifact_id, gate.handle_id, gate.gated_observation_id
            )
        ),
        ManifestHandoffSupervisorControlArtifactRole.RELEASE_CONSUMED: codec.encode(
            ManifestHandoffSupervisorReleaseConsumedDocument(
                gate.consumed_artifact_id, gate.handle_id, RELEASE
            )
        ),
    }


def test_observer_reads_exact_direct_ready_and_consumed_without_publish():
    gate = launch().gate
    codec, values = encoded_values(gate)
    reader = Reader(values)
    observer = ReadOnlyManifestHandoffSupervisorWrapperArtifactObserver(
        reader=reader, codec=codec
    )
    ready = observer.observe_ready(gate)
    consumed = observer.observe_consumed(gate, RELEASE)
    assert ready.role is ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY
    assert consumed.role is ManifestHandoffSupervisorControlArtifactRole.RELEASE_CONSUMED
    assert [request.role for request in reader.requests] == [ready.role, consumed.role]
    assert repr(observer) == "ReadOnlyManifestHandoffSupervisorWrapperArtifactObserver()"


def test_absence_is_neutral_and_never_persisted():
    gate = launch().gate
    codec = CanonicalManifestHandoffSupervisorControlArtifactCodec()
    observer = ReadOnlyManifestHandoffSupervisorWrapperArtifactObserver(
        reader=Reader({}), codec=codec
    )
    store = Artifacts()
    recorder = PersistentManifestHandoffSupervisorWrapperArtifactRecorder(
        observer=observer, control_artifacts=store
    )
    assert recorder.record_ready(gate) is None
    assert recorder.record_consumed(gate, RELEASE) is None
    assert store.requests == []


def test_divergent_direct_document_is_detail_free_and_not_recorded():
    gate = launch().gate
    codec = CanonicalManifestHandoffSupervisorControlArtifactCodec()
    divergent = codec.encode(ManifestHandoffSupervisorReadyDocument(
        gate.ready_artifact_id, ManifestHandoffSupervisorHandleId("other"),
        gate.gated_observation_id,
    ))
    observer = ReadOnlyManifestHandoffSupervisorWrapperArtifactObserver(
        reader=Reader({ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY: divergent}),
        codec=codec,
    )
    store = Artifacts()
    recorder = PersistentManifestHandoffSupervisorWrapperArtifactRecorder(
        observer=observer, control_artifacts=store
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        recorder.record_ready(gate)
    assert str(caught.value) == "manifest_handoff_registry_unavailable"
    assert store.requests == []


def test_recorder_persists_only_observed_exact_facts_and_preserves_conflict():
    gate = launch().gate
    codec, values = encoded_values(gate)
    observer = ReadOnlyManifestHandoffSupervisorWrapperArtifactObserver(
        reader=Reader(values), codec=codec
    )
    store = Artifacts()
    recorder = PersistentManifestHandoffSupervisorWrapperArtifactRecorder(
        observer=observer, control_artifacts=store
    )
    ready = recorder.record_ready(gate)
    consumed = recorder.record_consumed(gate, RELEASE)
    assert type(ready) is RecordedManifestHandoffSupervisorControlArtifact
    assert type(consumed) is RecordedManifestHandoffSupervisorControlArtifact
    assert len(store.requests) == 2
    conflict = PersistentManifestHandoffSupervisorWrapperArtifactRecorder(
        observer=observer, control_artifacts=Artifacts(conflict=True)
    ).record_ready(gate)
    assert type(conflict) is ManifestHandoffSupervisorRuntimeConflict


def test_source_surface_has_no_publish_execute_engine_or_authority():
    text = Path(
        "src/liquent_platform/application/manifest_handoff_supervisor_wrapper_artifact_observer.py"
    ).read_text(encoding="utf-8")
    for forbidden in (".publish(", "execute_writer", "execute_recovery", "SessionPrincipal",
                      "Permission", "allow", "engine.", "subprocess"):
        assert forbidden not in text


def test_terminal_observation_preserves_direct_outcome_and_exact_facts():
    gate = launch().gate
    codec = CanonicalManifestHandoffSupervisorControlArtifactCodec()
    outcome = CompletedManifestHandoffWriterProcess(
        gate.handle_id, launch().request.claim_id, launch().request.owner_id,
        ManifestHandoffWriterProcessKind.UNAVAILABLE, NOW,
    )
    encoded = codec.encode(ManifestHandoffSupervisorTerminalEnvelopeDocument(
        gate.terminal_artifact_id, gate.handle_id,
        gate.terminal_observation_id, outcome,
    ))
    observer = ReadOnlyManifestHandoffSupervisorWrapperArtifactObserver(
        reader=Reader({ManifestHandoffSupervisorControlArtifactRole.TERMINAL_ENVELOPE: encoded}),
        codec=codec,
    )
    observed = observer.observe_terminal(gate)
    assert observed.document.outcome == outcome
    assert observed.publication.facts == encoded.facts
    recorded = PersistentManifestHandoffSupervisorWrapperArtifactRecorder(
        observer=observer, control_artifacts=Artifacts()
    ).record_terminal(gate)
    assert recorded.observation.document.outcome == outcome
    assert recorded.record.facts == encoded.facts
