from datetime import datetime, timezone
from pathlib import Path

import pytest

from liquent_platform.application.manifest_handoff_supervisor_execution_reconciliation import (
    ReadOnlyManifestHandoffSupervisorExecutionReconciler,
)
from liquent_platform.identity.manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorBackendInstanceId,
    ManifestHandoffSupervisorPrepareId,
    ManifestHandoffSupervisorReleaseId,
)
from liquent_platform.identity.manifest_handoff_supervisor_engine import (
    ManifestHandoffSupervisorEngineState,
    ObservedManifestHandoffSupervisorContainer,
)
from liquent_platform.identity.manifest_handoff_supervisor_execution_reconciliation import (
    ManifestHandoffSupervisorExecutionReconciliationStatus as Status,
)
from liquent_platform.identity.manifest_handoff_supervisor_journal import (
    ManifestHandoffSupervisorJournalState,
    ManifestHandoffSupervisorLaunchCommitId,
    ManifestHandoffWriterJournalView,
    RegisterManifestHandoffWriterJournalJob,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_anchor import (
    ManifestHandoffSupervisorLaunchDocumentDigest,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    BoundManifestHandoffSupervisorRuntime,
    ManifestHandoffSupervisorControlArtifactFacts,
    ManifestHandoffSupervisorControlArtifactId,
    ManifestHandoffSupervisorControlArtifactRole,
    ManifestHandoffSupervisorRuntimeContainerId,
    RecordedManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from test_lq608_lq609_supervisor_launch_document import launch


NOW = datetime(2026, 8, 28, 12, tzinfo=timezone.utc)
RELEASE = ManifestHandoffSupervisorReleaseId("release-632")
FACTS = ManifestHandoffSupervisorControlArtifactFacts("a" * 64, 1)


def evidence(engine_state, *, journal_state=ManifestHandoffSupervisorJournalState.RELEASE_COMMITTED):
    document = launch()
    gate = document.gate
    registration = RegisterManifestHandoffWriterJournalJob(
        ManifestHandoffSupervisorBackendInstanceId("backend-632"),
        ManifestHandoffSupervisorPrepareId("prepare-632"),
        ManifestHandoffSupervisorLaunchCommitId("launch-commit-632"),
        gate.handle_id, document.request,
    )
    journal = ManifestHandoffWriterJournalView(
        registration, journal_state, NOW, release_id=RELEASE
    )
    runtime_id = ManifestHandoffSupervisorRuntimeContainerId("container-632")
    runtime = BoundManifestHandoffSupervisorRuntime(
        gate.handle_id, document.creation_id, runtime_id,
        gate.control_directory_id, document.image_digest, NOW,
    )
    observation = ObservedManifestHandoffSupervisorContainer(
        runtime_id, document.creation_id, document.image_digest,
        document.document_id, ManifestHandoffSupervisorLaunchDocumentDigest("b" * 64),
        gate.profile, engine_state, Path("/source"), Path("/target"),
    )
    token = artifact(
        ManifestHandoffSupervisorControlArtifactId("token-632"), gate.handle_id,
        ManifestHandoffSupervisorControlArtifactRole.RELEASE_TOKEN, RELEASE,
    )
    consumed = artifact(
        gate.consumed_artifact_id, gate.handle_id,
        ManifestHandoffSupervisorControlArtifactRole.RELEASE_CONSUMED, RELEASE,
    )
    terminal = artifact(
        gate.terminal_artifact_id, gate.handle_id,
        ManifestHandoffSupervisorControlArtifactRole.TERMINAL_ENVELOPE,
        gate.terminal_observation_id,
    )
    return journal, runtime, gate, observation, token, consumed, terminal


def artifact(identity, handle, role, correlation):
    return RecordedManifestHandoffSupervisorControlArtifact(
        identity, handle, role, correlation, FACTS, NOW
    )


@pytest.mark.parametrize("state,consumed,terminal,expected", [
    (ManifestHandoffSupervisorEngineState.RUNNING, False, False,
     Status.WAITING_FOR_CHILD_CONSUMPTION),
    (ManifestHandoffSupervisorEngineState.RUNNING, True, False,
     Status.CHILD_CAPABILITY_IN_FLIGHT),
    (ManifestHandoffSupervisorEngineState.EXITED, True, False,
     Status.AMBIGUOUS_AFTER_CONSUMPTION),
    (ManifestHandoffSupervisorEngineState.RUNNING, True, True,
     Status.WAITING_FOR_ENGINE_TERMINAL),
    (ManifestHandoffSupervisorEngineState.DEAD, True, True,
     Status.TERMINAL_EVIDENCE_READY),
])
def test_reconciliation_classifies_closed_crash_windows(state, consumed, terminal, expected):
    journal, runtime, gate, observation, token, consumed_fact, terminal_fact = evidence(state)
    result = ReadOnlyManifestHandoffSupervisorExecutionReconciler().reconcile(
        journal=journal, runtime=runtime, gate=gate, observation=observation,
        release_token=token,
        consumed=consumed_fact if consumed else None,
        terminal=terminal_fact if terminal else None,
    )
    assert result.status is expected
    assert result.may_start_child is False
    assert result.may_publish_release is False
    assert result.may_execute_capability is False


def test_running_journal_without_consumed_is_blocked_divergence():
    values = evidence(
        ManifestHandoffSupervisorEngineState.RUNNING,
        journal_state=ManifestHandoffSupervisorJournalState.RUNNING,
    )
    result = ReadOnlyManifestHandoffSupervisorExecutionReconciler().reconcile(
        journal=values[0], runtime=values[1], gate=values[2], observation=values[3],
        release_token=values[4],
    )
    assert result.status is Status.BLOCKED_DIVERGENCE


def test_divergent_consumed_release_is_blocked_without_restart_authority():
    journal, runtime, gate, observation, token, _, _ = evidence(
        ManifestHandoffSupervisorEngineState.RUNNING
    )
    divergent = artifact(
        gate.consumed_artifact_id, gate.handle_id,
        ManifestHandoffSupervisorControlArtifactRole.RELEASE_CONSUMED,
        ManifestHandoffSupervisorReleaseId("other-release"),
    )
    result = ReadOnlyManifestHandoffSupervisorExecutionReconciler().reconcile(
        journal=journal, runtime=runtime, gate=gate, observation=observation,
        release_token=token, consumed=divergent,
    )
    assert result.status is Status.BLOCKED_DIVERGENCE
    assert not result.may_start_child


def test_malformed_dependency_is_detail_free_unavailability():
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        ReadOnlyManifestHandoffSupervisorExecutionReconciler().reconcile(
            journal=None, runtime=None, gate=None, observation=None, release_token=None
        )
    assert str(caught.value) == "manifest_handoff_registry_unavailable"
