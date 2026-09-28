from __future__ import annotations

import os
from pathlib import Path

from tools.private_manifest_handoff_reconcile import reconcile_manifest_handoff


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


def test_absent_and_success_are_read_only(tmp_path: Path) -> None:
    root = _root(tmp_path)
    absent = reconcile_manifest_handoff(root, "attempt")
    assert absent.outcome == "manifest_absent"
    final = root / "attempt.json"
    _write(final)
    before = final.stat()
    success = reconcile_manifest_handoff(root, "attempt")
    after = final.stat()
    assert success.outcome == "manifest_handed_off"
    assert success.filename == "attempt.json"
    assert success.file_count == 1
    assert before.st_ino == after.st_ino
    assert final.read_bytes() == MANIFEST


def test_temporary_only_and_linked_pending_cleanup_are_distinct(tmp_path: Path) -> None:
    root = _root(tmp_path)
    temporary = root / ".attempt-abcdef.tmp"
    _write(temporary)
    temporary_only = reconcile_manifest_handoff(root, "attempt")
    assert temporary_only.outcome == "manifest_temporary_only"
    assert temporary_only.temporary_present is True
    final = root / "attempt.json"
    os.link(temporary, final)
    linked = reconcile_manifest_handoff(root, "attempt")
    assert linked.outcome == "manifest_handed_off_pending_cleanup"
    assert linked.temporary_present is True
    assert final.stat().st_ino == temporary.stat().st_ino


def test_foreign_final_or_multiple_temps_are_conflict(tmp_path: Path) -> None:
    root = _root(tmp_path)
    final = root / "attempt.json"
    final.symlink_to(root / "outside")
    assert reconcile_manifest_handoff(root, "attempt").outcome == "manifest_handoff_conflict"
    final.unlink()
    _write(root / ".attempt-first.tmp")
    _write(root / ".attempt-second.tmp")
    assert reconcile_manifest_handoff(root, "attempt").outcome == "manifest_handoff_conflict"


def test_different_final_and_temp_inodes_are_conflict(tmp_path: Path) -> None:
    root = _root(tmp_path)
    _write(root / "attempt.json")
    _write(root / ".attempt-other.tmp")
    assert reconcile_manifest_handoff(root, "attempt").outcome == "manifest_handoff_conflict"


def test_roadmap_links_read_only_reconciler_without_installation() -> None:
    root = Path(__file__).parents[1]
    roadmap = (root / "docs/technical-status-and-roadmap.md").read_text(
        encoding="utf-8"
    )
    project = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "- LQ-427 read-only private manifest handoff reconciliation:" in roadmap
    assert "`docs/lq-427-read-only-private-manifest-handoff-reconciliation.md`" in roadmap
    assert "nächster Slice LQ-428" in roadmap
    assert "private-manifest-handoff-reconcile" not in project
