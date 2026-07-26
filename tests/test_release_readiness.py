from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools.write_release_readiness import build_readiness


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "write_release_readiness.py"
REVISION = "8" * 40


def _evidence(**updates: object) -> dict[str, object]:
    run: dict[str, object] = {
        "head_sha": REVISION,
        "head_branch": "main",
        "path": ".github/workflows/quality.yml",
        "event": "push",
        "status": "completed",
        "conclusion": "success",
    }
    run.update(updates)
    return {"workflow_runs": [run]}


def test_readiness_verifies_quality_without_authorizing_publication() -> None:
    report = build_readiness(REVISION, "0.1.0", _evidence())

    assert report["quality_gate"]["verified"] is True
    assert report["publication"] == {
        "authorized": False,
        "performed": False,
        "required_confirmation": "PUBLISH",
        "workflow": ".github/workflows/release.yml",
    }
    assert report["deployment"] == {"authorized": False, "performed": False}


@pytest.mark.parametrize(
    "updates",
    [
        {"head_branch": "feature"},
        {"event": "pull_request"},
        {"status": "in_progress"},
        {"conclusion": "failure"},
    ],
)
def test_readiness_rejects_non_main_or_unsuccessful_evidence(
    updates: dict[str, object]
) -> None:
    with pytest.raises(ValueError):
        build_readiness(REVISION, "0.1.0", _evidence(**updates))


def test_cli_writes_deterministic_readiness_evidence(tmp_path: Path) -> None:
    quality_runs = tmp_path / "quality-runs.json"
    quality_runs.write_text(json.dumps(_evidence()), encoding="utf-8")
    output = tmp_path / "readiness.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--revision",
            REVISION,
            "--version",
            "0.1.0",
            "--quality-runs",
            str(quality_runs),
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )

    assert "release readiness verified" in completed.stdout
    assert json.loads(output.read_text(encoding="utf-8"))["candidate"] == {
        "revision": REVISION,
        "version": "0.1.0",
    }
