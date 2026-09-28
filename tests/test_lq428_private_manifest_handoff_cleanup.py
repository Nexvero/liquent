from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from tools.private_manifest_handoff_cleanup import (
    ManifestCleanupUnknown,
    cleanup_manifest_handoff,
)


MANIFEST = (
    b'{"base_commit":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","branch":null,'
    b'"commit_authorized":false,"deployment_authorized":false,"file_count":1,'
    b'"files":[{"mode":"0644","path":"docs/example.md",'
    b'"review_sections":["integration_preflight"],'
    b'"sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",'
    b'"size":1,"status":"untracked"}],"publishing_authorized":false,'
    b'"review_sections":["identity_authority","release_control_plane",'
    b'"research_jobs_worker","staging_recovery","runtime_cleanup_lineage",'
    b'"volume_disposition_deletion","integration_preflight"],'
    b'"schema_version":1,"staging_authorized":false}\n'
)


def _root(tmp_path: Path) -> Path:
    root = tmp_path.resolve() / "handoff"
    root.mkdir(mode=0o700)
    os.chmod(root, 0o700)
    return root


def _write(path: Path, value: bytes = MANIFEST) -> None:
    path.write_bytes(value)
    os.chmod(path, 0o600)


def test_pending_cleanup_removes_only_redundant_name(tmp_path: Path) -> None:
    root = _root(tmp_path)
    temporary = root / ".attempt-random.tmp"
    final = root / "attempt.json"
    _write(temporary)
    os.link(temporary, final)
    inode = final.stat().st_ino

    result = cleanup_manifest_handoff(root, "attempt")

    assert result.outcome == "manifest_handoff_cleanup_completed"
    assert result.observed_outcome == "manifest_handed_off"
    assert result.filename == "attempt.json"
    assert result.file_count == 1
    assert not temporary.exists()
    assert final.stat().st_ino == inode
    assert final.read_bytes() == MANIFEST


def test_absent_temporary_only_success_and_conflict_do_not_mutate(tmp_path: Path) -> None:
    root = _root(tmp_path)
    assert cleanup_manifest_handoff(root, "attempt").observed_outcome == "manifest_absent"

    temporary = root / ".attempt-only.tmp"
    _write(temporary)
    before = temporary.stat().st_ino
    result = cleanup_manifest_handoff(root, "attempt")
    assert result.observed_outcome == "manifest_temporary_only"
    assert temporary.stat().st_ino == before

    final = root / "attempt.json"
    _write(final)
    final_before = final.read_bytes()
    conflict = cleanup_manifest_handoff(root, "attempt")
    assert conflict.observed_outcome == "manifest_handoff_conflict"
    assert temporary.exists()
    assert final.read_bytes() == final_before

    temporary.unlink()
    success = cleanup_manifest_handoff(root, "attempt")
    assert success.observed_outcome == "manifest_handed_off"
    assert final.read_bytes() == final_before


def test_revalidation_conflict_preserves_both_names(tmp_path: Path) -> None:
    root = _root(tmp_path)
    temporary = root / ".attempt-random.tmp"
    final = root / "attempt.json"
    _write(temporary)
    os.link(temporary, final)

    with patch(
        "tools.private_manifest_handoff_cleanup._matching_temporary_names",
        return_value=[],
    ):
        result = cleanup_manifest_handoff(root, "attempt")

    assert result.outcome == "manifest_handoff_cleanup_conflict"
    assert temporary.exists()
    assert final.exists()


def test_failure_after_unlink_is_unknown_and_final_survives(tmp_path: Path) -> None:
    root = _root(tmp_path)
    temporary = root / ".attempt-random.tmp"
    final = root / "attempt.json"
    _write(temporary)
    os.link(temporary, final)

    with patch("tools.private_manifest_handoff_cleanup.os.fsync", side_effect=OSError("secret")):
        try:
            cleanup_manifest_handoff(root, "attempt")
        except ManifestCleanupUnknown as error:
            assert str(error) == "private manifest handoff cleanup outcome unknown"
        else:
            raise AssertionError("expected unknown cleanup outcome")

    assert not temporary.exists()
    assert final.read_bytes() == MANIFEST


def test_roadmap_links_cleanup_without_installation() -> None:
    root = Path(__file__).parents[1]
    roadmap = (root / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    project = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "- LQ-428 owner-controlled private manifest handoff cleanup:" in roadmap
    assert "`docs/lq-428-owner-controlled-private-manifest-handoff-cleanup.md`" in roadmap
    assert "nächster Slice LQ-429" in roadmap
    assert "private-manifest-handoff-cleanup" not in project
