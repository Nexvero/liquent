from __future__ import annotations

import os
from pathlib import Path

import pytest

import liquent_platform.operators.artifact_probe_recovery_remove as remove


TOKEN = "c" * 64
CONTENT = b'{"liquent_staging_artifact_probe":1}\n'


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    return root


def _probe(root: Path) -> Path:
    probe = root / f".liquent-staging-probe-{TOKEN}"
    probe.mkdir(mode=0o700)
    return probe


def _file(path: Path) -> None:
    path.write_bytes(CONTENT)
    os.chmod(path, 0o600)


@pytest.mark.parametrize("state", ["empty", "temporary", "final", "linked"])
def test_exact_state_is_revalidated_and_removed(tmp_path: Path, state: str) -> None:
    root = _root(tmp_path)
    probe = _probe(root)
    if state in {"temporary", "linked"}:
        _file(probe / ".capability.tmp")
    if state == "final":
        _file(probe / "capability.json")
    elif state == "linked":
        os.link(probe / ".capability.tmp", probe / "capability.json")
    assert remove.remove_probe_prefix(TOKEN, artifact_root=root) == "removed"
    assert list(root.iterdir()) == []


def test_absence_is_idempotent_and_does_not_create_prefix(tmp_path: Path) -> None:
    root = _root(tmp_path)
    assert remove.remove_probe_prefix(TOKEN, artifact_root=root) == "already_absent"
    assert list(root.iterdir()) == []


@pytest.mark.parametrize("state", ["unknown", "different", "symlink", "external_link"])
def test_conflict_is_not_changed(tmp_path: Path, state: str) -> None:
    root = _root(tmp_path)
    probe = _probe(root)
    if state == "unknown":
        _file(probe / "unknown")
    elif state == "different":
        (probe / "capability.json").write_bytes(b"different")
        os.chmod(probe / "capability.json", 0o600)
    elif state == "symlink":
        (probe / "capability.json").symlink_to("outside")
    else:
        _file(probe / "capability.json")
        os.link(probe / "capability.json", root / "outside")
    before = sorted(item.name for item in root.iterdir())
    assert remove.remove_probe_prefix(TOKEN, artifact_root=root) == "conflict"
    assert sorted(item.name for item in root.iterdir()) == before


def test_unknown_unlink_effect_stops_without_blind_remaining_cleanup(
    tmp_path: Path, monkeypatch,
) -> None:
    root = _root(tmp_path)
    probe = _probe(root)
    _file(probe / ".capability.tmp")
    os.link(probe / ".capability.tmp", probe / "capability.json")
    original = remove.os.unlink

    def unknown_unlink(*args, **kwargs):
        original(*args, **kwargs)
        raise OSError("lost acknowledgement")

    monkeypatch.setattr(remove.os, "unlink", unknown_unlink)
    with pytest.raises(remove.ArtifactProbeRecoveryRemoveUnavailable) as caught:
        remove.remove_probe_prefix(TOKEN, artifact_root=root)
    assert str(caught.value) == "artifact_probe_recovery_remove_unavailable"
    assert caught.value.__cause__ is None
    assert sorted(item.name for item in probe.iterdir()) == ["capability.json"]


def test_output_is_closed_and_cli_failure_is_silent(monkeypatch, capsys) -> None:
    monkeypatch.setattr(remove, "remove_probe_prefix", lambda _: "removed")
    assert remove.remove(TOKEN) == (
        b'{"operation":"artifact_probe_recovery_remove","outcome":"removed",'
        b'"schema_version":1}\n'
    )
    monkeypatch.undo()
    assert remove.main(["--run-token", "bad"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
