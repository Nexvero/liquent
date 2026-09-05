from datetime import datetime, timezone
import inspect
from pathlib import Path

import pytest

from liquent_platform.identity.manifest_handoff import (
    ManifestHandoffExecutionClaimId,
    ManifestHandoffExecutionOwnerId,
    ManifestHandoffFacts,
    ManifestHandoffName,
    ManifestHandoffRecoveryClaimId,
    ManifestHandoffRecoveryOwnerId,
    ManifestHandoffRegistryScopeId,
    ManifestHandoffScopeBinding,
)
from liquent_platform.identity.manifest_handoff_supervisor import (
    CompletedManifestHandoffRecoveryProcess,
    CompletedManifestHandoffWriterProcess,
    ManifestHandoffRecoveryProcessKind,
    ManifestHandoffRecoverySupervisorRequest,
    ManifestHandoffSupervisorConflict,
    ManifestHandoffSupervisorHandleId,
    ManifestHandoffWriterProcessKind,
    ManifestHandoffWriterSupervisorRequest,
    PreparedManifestHandoffRecoveryProcess,
    PreparedManifestHandoffWriterProcess,
    RunningManifestHandoffRecoveryProcess,
    RunningManifestHandoffWriterProcess,
)
from liquent_platform.identity.ports import (
    ControlledManifestHandoffRecoverySupervisor,
    ControlledManifestHandoffWriterSupervisor,
)


NOW = datetime(2026, 8, 25, 2, tzinfo=timezone.utc)
HANDLE = ManifestHandoffSupervisorHandleId("handle-446")
EXECUTION = ManifestHandoffExecutionClaimId("execution-446")
EXECUTION_OWNER = ManifestHandoffExecutionOwnerId("execution-owner-446")
RECOVERY = ManifestHandoffRecoveryClaimId("recovery-446")
RECOVERY_OWNER = ManifestHandoffRecoveryOwnerId("recovery-owner-446")
BINDING = ManifestHandoffScopeBinding(
    ManifestHandoffRegistryScopeId("scope-446"),
    Path("/controlled/source"),
    Path("/private/target"),
)
NAME = ManifestHandoffName("handoff-446")
FACTS = ManifestHandoffFacts("a" * 64, 6)


def test_requests_are_closed_repr_safe_and_have_no_process_controls() -> None:
    writer = ManifestHandoffWriterSupervisorRequest(
        EXECUTION, EXECUTION_OWNER, BINDING, NAME
    )
    recovery = ManifestHandoffRecoverySupervisorRequest(
        RECOVERY, RECOVERY_OWNER, BINDING, NAME
    )
    assert set(writer.__dataclass_fields__) == {
        "claim_id", "owner_id", "binding", "handoff_name"
    }
    assert set(recovery.__dataclass_fields__) == set(writer.__dataclass_fields__)
    forbidden = {
        "command", "args", "env", "cwd", "shell", "timeout", "signal",
        "allow", "role", "authority", "handle_id",
    }
    assert not forbidden & set(writer.__dataclass_fields__)
    assert "execution-446" not in repr(writer)
    assert "/controlled/source" not in repr(writer)
    assert "recovery-owner-446" not in repr(recovery)


def test_prepared_and_running_writer_states_fix_gate_and_terminal_flags() -> None:
    prepared = PreparedManifestHandoffWriterProcess(
        HANDLE, EXECUTION, EXECUTION_OWNER, NOW
    )
    running = RunningManifestHandoffWriterProcess(
        HANDLE, EXECUTION, EXECUTION_OWNER, NOW
    )
    assert prepared.gate_released is False
    assert prepared.writer_authorized is False
    assert running.gate_released is True and running.terminal is False
    assert "handle-446" not in repr(prepared)
    with pytest.raises(TypeError):
        PreparedManifestHandoffWriterProcess(
            HANDLE, EXECUTION, EXECUTION_OWNER, NOW, gate_released=True
        )


def test_writer_terminal_outcomes_have_exact_success_fact_matrix() -> None:
    success = CompletedManifestHandoffWriterProcess(
        HANDLE,
        EXECUTION,
        EXECUTION_OWNER,
        ManifestHandoffWriterProcessKind.MANIFEST_HANDED_OFF,
        NOW,
        "handoff-446.json",
        FACTS,
    )
    assert success.terminal is True
    assert success.commit_authorized is False
    assert success.staging_authorized is False
    for kind in ManifestHandoffWriterProcessKind:
        if kind is ManifestHandoffWriterProcessKind.MANIFEST_HANDED_OFF:
            continue
        value = CompletedManifestHandoffWriterProcess(
            HANDLE, EXECUTION, EXECUTION_OWNER, kind, NOW
        )
        assert value.filename is None and value.facts is None
    with pytest.raises(ValueError):
        CompletedManifestHandoffWriterProcess(
            HANDLE,
            EXECUTION,
            EXECUTION_OWNER,
            ManifestHandoffWriterProcessKind.MANIFEST_HANDED_OFF,
            NOW,
            "../bad.json",
            FACTS,
        )


def test_recovery_states_never_authorize_writer_or_cleanup() -> None:
    prepared = PreparedManifestHandoffRecoveryProcess(
        HANDLE, RECOVERY, RECOVERY_OWNER, NOW
    )
    running = RunningManifestHandoffRecoveryProcess(
        HANDLE, RECOVERY, RECOVERY_OWNER, NOW
    )
    assert prepared.gate_released is False
    assert prepared.writer_authorized is False
    assert prepared.cleanup_authorized is False
    assert running.writer_authorized is False
    assert running.cleanup_authorized is False
    assert running.gate_released is True and running.terminal is False


@pytest.mark.parametrize(
    "kind,filename,facts",
    (
        (ManifestHandoffRecoveryProcessKind.MANIFEST_ABSENT, None, None),
        (ManifestHandoffRecoveryProcessKind.MANIFEST_TEMPORARY_ONLY, None, FACTS),
        (ManifestHandoffRecoveryProcessKind.MANIFEST_HANDED_OFF, "handoff-446.json", FACTS),
        (ManifestHandoffRecoveryProcessKind.MANIFEST_HANDED_OFF_PENDING_CLEANUP, "handoff-446.json", FACTS),
        (ManifestHandoffRecoveryProcessKind.MANIFEST_HANDOFF_CONFLICT, None, None),
        (ManifestHandoffRecoveryProcessKind.OUTCOME_UNKNOWN, None, None),
    ),
)
def test_recovery_terminal_outcome_matrix(kind, filename, facts) -> None:
    value = CompletedManifestHandoffRecoveryProcess(
        HANDLE, RECOVERY, RECOVERY_OWNER, kind, NOW, filename, facts
    )
    assert value.terminal is True
    assert value.writer_authorized is False
    assert value.cleanup_authorized is False


def test_writer_and_recovery_ports_are_separate_and_closed() -> None:
    writer_methods = {
        name: value
        for name, value in ControlledManifestHandoffWriterSupervisor.__dict__.items()
        if callable(value) and not name.startswith("_")
    }
    recovery_methods = {
        name: value
        for name, value in ControlledManifestHandoffRecoverySupervisor.__dict__.items()
        if callable(value) and not name.startswith("_")
    }
    assert set(writer_methods) == {
        "prepare_writer", "release_writer", "inspect_writer", "terminate_writer"
    }
    assert set(recovery_methods) == {
        "prepare_recovery", "release_recovery", "inspect_recovery", "terminate_recovery"
    }
    for methods in (writer_methods, recovery_methods):
        for method in methods.values():
            parameters = set(inspect.signature(method).parameters)
            assert not parameters & {
                "command", "args", "env", "cwd", "shell", "timeout", "signal",
                "now", "allow", "role", "authority",
            }
    assert repr(ManifestHandoffSupervisorConflict()) == "ManifestHandoffSupervisorConflict()"


def test_roadmap_records_supervisor_types_and_next_slice() -> None:
    roadmap = (Path(__file__).parents[1] / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-446 manifest handoff supervisor types and closed ports:" in roadmap
    assert "`docs/lq-446-manifest-handoff-supervisor-types-and-closed-ports.md`" in roadmap
    assert "nächster Slice LQ-447" in roadmap
