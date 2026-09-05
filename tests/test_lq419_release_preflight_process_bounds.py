from __future__ import annotations

import json
from pathlib import Path
import sys
import time

from tools.controlled_release_preflight import ControlledReleasePreflight, PHASES
from tools.local_release_preflight_gates import (
    LocalGateRejected,
    _bounded_subprocess,
)


COMMIT = "a" * 40


def _rejected(operation) -> None:
    try:
        operation()
    except LocalGateRejected as error:
        assert str(error) == "local release preflight gate rejected"
    else:
        raise AssertionError("expected detail-limited rejection")


def _run(tmp_path: Path, script: str, *, timeout: float = 2.0, limit: int = 128):
    return _bounded_subprocess(
        (sys.executable, "-c", script),
        tmp_path,
        {},
        timeout_seconds=timeout,
        max_output_bytes=limit,
    )


def test_bounded_process_returns_only_complete_output(tmp_path: Path) -> None:
    result = _run(tmp_path, "import sys;sys.stdout.write('ok');sys.stderr.write('warn')")
    assert result.stdout == b"ok"
    assert result.stderr == b"warn"


def test_timeout_is_killed_and_rejected_without_waiting_for_natural_exit(
    tmp_path: Path,
) -> None:
    started = time.monotonic()
    _rejected(lambda: _run(tmp_path, "import time;time.sleep(10)", timeout=0.1))
    assert time.monotonic() - started < 3.0


def test_nonzero_or_oversized_output_is_detail_free(tmp_path: Path) -> None:
    _rejected(lambda: _run(tmp_path, "raise SystemExit(7)"))
    _rejected(lambda: _run(tmp_path, "print('x' * 129)", limit=128))
    _rejected(
        lambda: _run(
            tmp_path,
            "import sys;sys.stdout.write('x'*80);sys.stderr.write('y'*80)",
            limit=128,
        )
    )


class Gate:
    def __init__(self, phase: str, fail: bool = False) -> None:
        self.phase = phase
        self.fail = fail

    def execute(self, workspace: Path) -> bytes:
        (workspace / f"private-{self.phase}").write_text("private", encoding="ascii")
        if self.fail:
            raise RuntimeError("unknown process outcome with secret detail")
        facts = "f" * 64
        return (
            json.dumps(
                {
                    "facts_sha256": facts,
                    "phase": self.phase,
                    "schema_version": 1,
                    "source_commit": COMMIT,
                    "status": "passed",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("ascii")


def test_unknown_outcome_removes_all_private_artifacts(tmp_path: Path) -> None:
    gates = {phase: Gate(phase, fail=phase == "wheel") for phase in PHASES}
    output = tmp_path / "result"
    try:
        ControlledReleasePreflight(gates).run(output)
    except Exception as error:
        assert str(error) == "controlled release preflight rejected"
    else:
        raise AssertionError("expected rejection")
    assert not output.exists()
    assert list(tmp_path.iterdir()) == []


def test_successful_or_owner_existing_target_is_never_reused(tmp_path: Path) -> None:
    output = tmp_path / "retained-result"
    output.mkdir()
    marker = output / "retained-owner-evidence"
    marker.write_text("retain", encoding="ascii")
    gates = {phase: Gate(phase) for phase in PHASES}
    try:
        ControlledReleasePreflight(gates).run(output)
    except Exception as error:
        assert str(error) == "controlled release preflight rejected"
    else:
        raise AssertionError("expected rejection")
    assert marker.read_text(encoding="ascii") == "retain"
