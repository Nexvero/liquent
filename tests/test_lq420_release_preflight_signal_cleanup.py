from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import signal
import sys

from tools.controlled_release_preflight import (
    PHASES,
    ControlledPreflightRejected,
    ControlledReleasePreflight,
)
from tools.local_release_preflight_gates import _bounded_subprocess


COMMIT = "a" * 40


def _receipt(phase: str) -> bytes:
    return (
        json.dumps(
            {
                "facts_sha256": hashlib.sha256(phase.encode()).hexdigest(),
                "phase": phase,
                "schema_version": 1,
                "source_commit": COMMIT,
                "status": "passed",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("ascii")


class Gate:
    def __init__(self, phase: str, interrupt: int | None = None) -> None:
        self.phase = phase
        self.interrupt = interrupt

    def execute(self, workspace: Path) -> bytes:
        artifacts = workspace / "artifacts"
        if self.phase == "distributions":
            artifacts.mkdir(mode=0o700)
        if artifacts.exists():
            (artifacts / f"private-{self.phase}").write_text(
                "private", encoding="ascii"
            )
        created = {
            "entrypoints": "installed-wheel",
            "sdist": "sdist-wheel-roundtrip",
            "bundle": "bundle",
        }.get(self.phase)
        if created is not None:
            (workspace / created).mkdir(mode=0o700)
        if self.interrupt is not None:
            os.kill(os.getpid(), self.interrupt)
        return _receipt(self.phase)


def _interrupted(tmp_path: Path, interrupt: int) -> None:
    gates = {
        phase: Gate(phase, interrupt if phase == "normal_tests" else None)
        for phase in PHASES
    }
    output = tmp_path / "result"
    try:
        ControlledReleasePreflight(gates).run(output)
    except ControlledPreflightRejected as error:
        assert str(error) == "controlled release preflight rejected"
    else:
        raise AssertionError("expected signal rejection")
    assert not output.exists()
    assert list(tmp_path.iterdir()) == []


def test_sigint_and_sigterm_remove_private_workspace_without_success(
    tmp_path: Path,
) -> None:
    for interrupt in (signal.SIGINT, signal.SIGTERM):
        attempt = tmp_path / str(interrupt)
        attempt.mkdir()
        _interrupted(attempt, interrupt)
        attempt.rmdir()


class ChildInterruptGate:
    def __init__(self, phase: str) -> None:
        self.phase = phase

    def execute(self, workspace: Path) -> bytes:
        if self.phase == "postgres_tests":
            _bounded_subprocess(
                (
                    sys.executable,
                    "-c",
                    "import os,signal,time;"
                    "os.kill(os.getppid(),signal.SIGTERM);time.sleep(30)",
                ),
                workspace,
                {},
                timeout_seconds=60.0,
                max_output_bytes=128,
            )
        return _receipt(self.phase)


def test_signal_during_child_wait_kills_child_group_and_cleans_workspace(
    tmp_path: Path,
) -> None:
    gates = {phase: ChildInterruptGate(phase) for phase in PHASES}
    output = tmp_path / "result"
    try:
        ControlledReleasePreflight(gates).run(output)
    except ControlledPreflightRejected as error:
        assert str(error) == "controlled release preflight rejected"
    else:
        raise AssertionError("expected interrupted child rejection")
    assert not output.exists()
    assert list(tmp_path.iterdir()) == []


def test_signal_handlers_are_restored_after_success_or_rejection(tmp_path: Path) -> None:
    before = {item: signal.getsignal(item) for item in (signal.SIGINT, signal.SIGTERM)}
    gates = {phase: Gate(phase) for phase in PHASES}
    ControlledReleasePreflight(gates).run(tmp_path / "success")
    after_success = {
        item: signal.getsignal(item) for item in (signal.SIGINT, signal.SIGTERM)
    }
    assert after_success == before

    rejecting = {
        phase: Gate(phase, signal.SIGTERM if phase == "wheel" else None)
        for phase in PHASES
    }
    try:
        ControlledReleasePreflight(rejecting).run(tmp_path / "rejected")
    except ControlledPreflightRejected:
        pass
    else:
        raise AssertionError("expected rejection")
    assert {
        item: signal.getsignal(item) for item in (signal.SIGINT, signal.SIGTERM)
    } == before


def test_cli_still_normalizes_signal_rejection_without_authorization() -> None:
    source = Path("tools/run_controlled_release_preflight.py").read_text(
        encoding="utf-8"
    )
    assert "except ControlledPreflightRejected" in source
    assert '"error": "controlled_release_preflight_rejected"' in source
    assert '"publishing_authorized": False' in source
    assert '"deployment_authorized": False' in source
