from dataclasses import FrozenInstanceError
import threading

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_process_status import (
    ManifestHandoffSupervisorEngineApiProcessPhase,
    ManifestHandoffSupervisorEngineApiProcessSnapshot,
    ManifestHandoffSupervisorEngineApiProcessStatus,
    ManifestHandoffSupervisorEngineApiReadinessProbe,
)


def test_complete_normal_lifecycle_has_fixed_detail_free_snapshots() -> None:
    status = ManifestHandoffSupervisorEngineApiProcessStatus()
    expected = (
        ("initial", True, False, False),
        ("starting", True, False, False),
        ("serving", True, True, False),
        ("stopping", True, False, False),
        ("stopped", False, False, True),
    )
    moves = (
        None, status.mark_starting, status.mark_serving,
        status.mark_stopping, status.mark_stopped,
    )
    for move, values in zip(moves, expected, strict=True):
        if move is not None:
            move()
        snapshot = status.snapshot()
        assert snapshot.phase.value == values[0]
        assert (snapshot.live, snapshot.ready, snapshot.terminal) == values[1:]
        assert snapshot.reason == f"manifest_handoff_supervisor_engine_api_{values[0]}" or (
            values[0] == "serving"
            and snapshot.reason == "manifest_handoff_supervisor_engine_api_ready"
        )


@pytest.mark.parametrize("advance", (0, 1, 2, 3))
def test_failure_is_terminal_from_every_nonterminal_phase(advance: int) -> None:
    status = ManifestHandoffSupervisorEngineApiProcessStatus()
    moves = (status.mark_starting, status.mark_serving, status.mark_stopping)
    for move in moves[:advance]:
        move()
    status.mark_failed()
    snapshot = status.snapshot()
    assert snapshot == ManifestHandoffSupervisorEngineApiProcessSnapshot(
        ManifestHandoffSupervisorEngineApiProcessPhase.FAILED,
        False, False, True,
        "manifest_handoff_supervisor_engine_api_unavailable",
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        status.mark_failed()


@pytest.mark.parametrize("method", (
    "mark_serving", "mark_stopping", "mark_stopped",
))
def test_skipped_initial_transition_fails_closed(method: str) -> None:
    status = ManifestHandoffSupervisorEngineApiProcessStatus()
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        getattr(status, method)()
    assert status.snapshot().phase is ManifestHandoffSupervisorEngineApiProcessPhase.INITIAL


def test_stopped_is_terminal_and_cannot_restart_or_fail() -> None:
    status = ManifestHandoffSupervisorEngineApiProcessStatus()
    status.mark_starting()
    status.mark_stopping()
    status.mark_stopped()
    for method in (
        status.mark_starting, status.mark_serving, status.mark_stopping,
        status.mark_stopped, status.mark_failed,
    ):
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            method()


def test_snapshot_is_frozen_and_repr_contains_no_private_detail() -> None:
    status = ManifestHandoffSupervisorEngineApiProcessStatus()
    snapshot = status.snapshot()
    with pytest.raises(FrozenInstanceError):
        snapshot.ready = True
    assert repr(status) == "ManifestHandoffSupervisorEngineApiProcessStatus()"
    assert "lock" not in repr(status)


def test_readiness_probe_projects_every_phase_without_extra_authority() -> None:
    status = ManifestHandoffSupervisorEngineApiProcessStatus()
    probe = ManifestHandoffSupervisorEngineApiReadinessProbe(status)
    assert probe.check().ready is False
    status.mark_starting()
    assert probe.check().reason.endswith("_starting")
    status.mark_serving()
    assert probe.check().ready is True
    status.mark_stopping()
    assert probe.check().ready is False
    status.mark_stopped()
    assert probe.check().reason.endswith("_stopped")


def test_probe_fails_closed_if_snapshot_boundary_breaks(monkeypatch) -> None:
    status = ManifestHandoffSupervisorEngineApiProcessStatus()
    probe = ManifestHandoffSupervisorEngineApiReadinessProbe(status)
    monkeypatch.setattr(
        ManifestHandoffSupervisorEngineApiProcessStatus,
        "snapshot", lambda self: object(),
    )
    result = probe.check()
    assert result.ready is False
    assert result.reason == "manifest_handoff_supervisor_engine_api_unavailable"


def test_only_exact_status_can_back_probe() -> None:
    for value in (None, object(), "status"):
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            ManifestHandoffSupervisorEngineApiReadinessProbe(value)


def test_concurrent_transition_has_one_winner_and_no_partial_state() -> None:
    status = ManifestHandoffSupervisorEngineApiProcessStatus()
    outcomes = []

    def start() -> None:
        try:
            status.mark_starting()
            outcomes.append("started")
        except ManifestHandoffRegistryUnavailable:
            outcomes.append("rejected")

    threads = [threading.Thread(target=start) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert outcomes.count("started") == 1
    assert outcomes.count("rejected") == 7
    assert status.snapshot().phase is ManifestHandoffSupervisorEngineApiProcessPhase.STARTING
