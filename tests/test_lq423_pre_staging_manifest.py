from __future__ import annotations

import json
from pathlib import Path

from tools.pre_staging_manifest import (
    REVIEW_SECTIONS,
    PreStagingManifestRejected,
    build_manifest,
)


COMMIT = "a" * 40


class Git:
    def __init__(self, status: bytes, branch: bytes = b"") -> None:
        self.status = status
        self.branch = branch

    def __call__(self, argv, root: Path) -> bytes:
        if tuple(argv) == ("git", "rev-parse", "HEAD"):
            return COMMIT.encode()
        if tuple(argv) == ("git", "branch", "--show-current"):
            return self.branch
        if tuple(argv) == (
            "git",
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
        ):
            return self.status
        raise AssertionError(tuple(argv))


def _rejected(operation) -> None:
    try:
        operation()
    except PreStagingManifestRejected as error:
        assert str(error) == "pre-staging manifest rejected"
    else:
        raise AssertionError("expected rejection")


def test_manifest_is_sorted_deterministic_and_content_bound(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "tools").mkdir()
    (tmp_path / "docs/lq-423-example.md").write_text("doc\n", encoding="ascii")
    (tmp_path / "tools/pre_staging_manifest.py").write_text("tool\n", encoding="ascii")
    status = b"?? tools/pre_staging_manifest.py\0?? docs/lq-423-example.md\0"

    first = build_manifest(tmp_path, command_runner=Git(status))
    second = build_manifest(tmp_path, command_runner=Git(status))

    assert first == second
    assert first["file_count"] == 2
    assert [item["path"] for item in first["files"]] == [
        "docs/lq-423-example.md",
        "tools/pre_staging_manifest.py",
    ]
    assert all(item["review_sections"] == ["integration_preflight"] for item in first["files"])
    assert first["branch"] is None


def test_manifest_never_authorizes_git_or_external_actions(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("content\n", encoding="ascii")
    manifest = build_manifest(
        tmp_path, command_runner=Git(b" M pyproject.toml\0", branch=b"review\n")
    )
    assert manifest["review_sections"] == list(REVIEW_SECTIONS)
    assert manifest["files"][0]["review_sections"] == list(REVIEW_SECTIONS)
    for key in (
        "staging_authorized",
        "commit_authorized",
        "publishing_authorized",
        "deployment_authorized",
    ):
        assert manifest[key] is False


def test_staged_deleted_renamed_or_scope_foreign_record_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/file.md").write_text("x", encoding="ascii")
    for status in (
        b"M  docs/file.md\0",
        b" D docs/file.md\0",
        b"R  docs/file.md\0docs/other.md\0",
        b"?? README.md\0",
    ):
        _rejected(lambda status=status: build_manifest(tmp_path, command_runner=Git(status)))


def test_symlink_duplicate_empty_or_noncanonical_path_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    target = tmp_path / "target"
    target.write_text("owner", encoding="ascii")
    (tmp_path / "docs/link").symlink_to(target)
    cases = (
        b"?? docs/link\0",
        b"?? docs/missing\0",
        b"?? docs/../target\0",
        b"?? docs/link\0?? docs/link\0",
        b"",
    )
    for status in cases:
        _rejected(lambda status=status: build_manifest(tmp_path, command_runner=Git(status)))


def test_symbolic_parent_directory_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "file.md").write_text("owner", encoding="ascii")
    (tmp_path / "docs").symlink_to(outside, target_is_directory=True)
    _rejected(
        lambda: build_manifest(
            tmp_path, command_runner=Git(b"?? docs/file.md\0")
        )
    )


def test_roadmap_links_manifest_without_staging_authority() -> None:
    root = Path(__file__).parents[1]
    roadmap = (root / "docs/technical-status-and-roadmap.md").read_text(
        encoding="utf-8"
    )
    assert "- LQ-423 deterministic file-level pre-staging manifest:" in roadmap
    assert "`docs/lq-423-deterministic-file-level-pre-staging-manifest.md`" in roadmap
    assert "nächster Slice LQ-424" in roadmap
