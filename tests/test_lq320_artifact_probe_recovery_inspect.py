from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import liquent_platform.operators.artifact_probe_recovery_inspect as inspect


TOKEN = "b" * 64
CONTENT = b'{"liquent_staging_artifact_probe":1}\n'


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    return root


def _probe(root: Path) -> Path:
    value = root / f".liquent-staging-probe-{TOKEN}"
    value.mkdir(mode=0o700)
    return value


def _file(path: Path) -> None:
    path.write_bytes(CONTENT)
    os.chmod(path, 0o600)


def test_absence_is_neutral_and_does_not_create_prefix(tmp_path: Path) -> None:
    root = _root(tmp_path)
    assert inspect.classify_probe_prefix(TOKEN, artifact_root=root) == "absent"
    assert list(root.iterdir()) == []


@pytest.mark.parametrize("state", ["empty", "temporary", "final", "linked"])
def test_exact_reachable_states_are_recoverable_without_mutation(
    tmp_path: Path, state: str,
) -> None:
    root = _root(tmp_path)
    probe = _probe(root)
    if state in {"temporary", "linked"}:
        _file(probe / ".capability.tmp")
    if state == "final":
        _file(probe / "capability.json")
    elif state == "linked":
        os.link(probe / ".capability.tmp", probe / "capability.json")
    before = {
        item.name: (item.stat().st_ino, item.read_bytes())
        for item in probe.iterdir()
    }
    assert inspect.classify_probe_prefix(TOKEN, artifact_root=root) == "recoverable"
    after = {
        item.name: (item.stat().st_ino, item.read_bytes())
        for item in probe.iterdir()
    }
    assert after == before


@pytest.mark.parametrize("mutation", [
    "unknown", "bad_content", "bad_mode", "independent", "symlink", "hardlink",
])
def test_unowned_or_unreachable_state_is_conflict(
    tmp_path: Path, mutation: str,
) -> None:
    root = _root(tmp_path)
    probe = _probe(root)
    if mutation == "unknown":
        _file(probe / "other")
    elif mutation == "bad_content":
        (probe / "capability.json").write_bytes(b"different")
        os.chmod(probe / "capability.json", 0o600)
    elif mutation == "bad_mode":
        _file(probe / "capability.json")
        os.chmod(probe / "capability.json", 0o644)
    elif mutation == "independent":
        _file(probe / ".capability.tmp")
        _file(probe / "capability.json")
    elif mutation == "symlink":
        (probe / "capability.json").symlink_to("outside")
    else:
        _file(probe / "capability.json")
        os.link(probe / "capability.json", root / "outside-link")
    assert inspect.classify_probe_prefix(TOKEN, artifact_root=root) == "conflict"


def test_prefix_symlink_is_conflict_and_target_is_not_read(tmp_path: Path) -> None:
    root = _root(tmp_path)
    target = tmp_path / "target"
    target.mkdir()
    secret = target / "secret"
    secret.write_bytes(b"not-probe-content")
    (root / f".liquent-staging-probe-{TOKEN}").symlink_to(target)
    assert inspect.classify_probe_prefix(TOKEN, artifact_root=root) == "conflict"
    assert secret.read_bytes() == b"not-probe-content"


def test_output_is_closed_and_cli_failure_is_silent(monkeypatch, capsys) -> None:
    monkeypatch.setattr(inspect, "classify_probe_prefix", lambda _: "recoverable")
    assert json.loads(inspect.inspect(TOKEN)) == {
        "schema_version": 1,
        "inspection": "artifact_probe_recovery",
        "outcome": "recoverable",
    }
    monkeypatch.undo()
    assert inspect.main(["--run-token", "bad"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_error_is_stable_detail_free() -> None:
    error = inspect.ArtifactProbeRecoveryInspectUnavailable()
    assert str(error) == "artifact_probe_recovery_inspect_unavailable"
    assert error.__cause__ is None
