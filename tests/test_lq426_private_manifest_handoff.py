from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from tools.private_manifest_handoff import (
    ManifestHandoffUnavailable,
    ManifestHandoffUnknown,
    handoff_manifest,
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


def _roots(tmp_path: Path) -> tuple[Path, Path]:
    tmp_path = tmp_path.resolve()
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir(mode=0o700)
    target.mkdir(mode=0o700)
    os.chmod(source, 0o700)
    os.chmod(target, 0o700)
    return source, target


def test_success_is_private_exact_and_no_overwrite(tmp_path: Path) -> None:
    source, target = _roots(tmp_path)
    with patch("tools.private_manifest_handoff.render_manifest", return_value=MANIFEST):
        result = handoff_manifest(source, target, "attempt-426")
    final = target / "attempt-426.json"
    assert result.outcome == "manifest_handed_off"
    assert result.filename == final.name
    assert result.file_count == 1
    assert final.read_bytes() == MANIFEST
    assert final.stat().st_mode & 0o777 == 0o600
    assert list(target.iterdir()) == [final]

    with patch("tools.private_manifest_handoff.render_manifest") as generator:
        second = handoff_manifest(source, target, "attempt-426")
    assert second.outcome == "target_not_absent"
    generator.assert_not_called()
    assert final.read_bytes() == MANIFEST


def test_invalid_root_name_mode_or_symlink_is_detail_free(tmp_path: Path) -> None:
    source, target = _roots(tmp_path)
    cases = (
        (source, target, "../bad"),
        (source, target, "bad/name"),
        (source, source / "inside", "attempt"),
    )
    (source / "inside").mkdir(mode=0o700)
    for arguments in cases:
        try:
            handoff_manifest(*arguments)
        except ManifestHandoffUnavailable as error:
            assert str(error) == "private manifest handoff unavailable"
        else:
            raise AssertionError("expected unavailable")

    os.chmod(target, 0o755)
    try:
        handoff_manifest(source, target, "attempt")
    except ManifestHandoffUnavailable:
        pass
    else:
        raise AssertionError("expected mode rejection")


def test_failure_before_link_cleans_temporary_file(tmp_path: Path) -> None:
    source, target = _roots(tmp_path)
    with patch("tools.private_manifest_handoff.render_manifest", return_value=MANIFEST), patch(
        "tools.private_manifest_handoff.os.fsync", side_effect=OSError("secret")
    ):
        try:
            handoff_manifest(source, target, "attempt")
        except ManifestHandoffUnavailable as error:
            assert str(error) == "private manifest handoff unavailable"
        else:
            raise AssertionError("expected unavailable")
    assert list(target.iterdir()) == []


def test_failure_after_link_is_unknown_and_preserves_reconciliation_state(
    tmp_path: Path,
) -> None:
    source, target = _roots(tmp_path)
    calls = 0
    real_sync = os.fsync

    def fail_directory_sync(descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("unknown secret detail")
        real_sync(descriptor)

    with patch("tools.private_manifest_handoff.render_manifest", return_value=MANIFEST), patch(
        "tools.private_manifest_handoff.os.fsync", side_effect=fail_directory_sync
    ):
        try:
            handoff_manifest(source, target, "attempt")
        except ManifestHandoffUnknown as error:
            assert str(error) == "private manifest handoff outcome unknown"
        else:
            raise AssertionError("expected unknown")
    names = sorted(path.name for path in target.iterdir())
    assert "attempt.json" in names
    assert any(name.startswith(".attempt-") for name in names)


def test_roadmap_links_writer_without_installed_or_git_authority() -> None:
    root = Path(__file__).parents[1]
    roadmap = (root / "docs/technical-status-and-roadmap.md").read_text(
        encoding="utf-8"
    )
    project = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "- LQ-426 owner-controlled private manifest writer:" in roadmap
    assert "`docs/lq-426-owner-controlled-private-manifest-writer.md`" in roadmap
    assert "nächster Slice LQ-427" in roadmap
    assert "private-manifest-handoff" not in project
