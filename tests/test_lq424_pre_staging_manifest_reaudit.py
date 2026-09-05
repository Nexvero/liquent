from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from tools.pre_staging_manifest import (
    REVIEW_SECTIONS,
    PreStagingManifestRejected,
    build_manifest,
)


COMMIT = "a" * 40


def _real_manifest(root: Path) -> dict[str, object]:
    try:
        return build_manifest(root)
    except PreStagingManifestRejected:
        status = subprocess.run(
            ("git", "status", "--porcelain=v1", "--untracked-files=all"),
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout
        if status:
            raise
        pytest.skip("pre-staging manifest is not applicable to a clean tree")


class DriftingGit:
    def __init__(self, statuses: list[bytes], commits: list[bytes] | None = None) -> None:
        self.statuses = iter(statuses)
        self.commits = iter(commits or [COMMIT.encode(), COMMIT.encode()])

    def __call__(self, argv, root: Path) -> bytes:
        command = tuple(argv)
        if command == ("git", "rev-parse", "HEAD"):
            return next(self.commits)
        if command == ("git", "branch", "--show-current"):
            return b""
        if command[-1] == "--untracked-files=all":
            return next(self.statuses)
        raise AssertionError(command)


def _rejected(operation) -> None:
    try:
        operation()
    except PreStagingManifestRejected as error:
        assert str(error) == "pre-staging manifest rejected"
    else:
        raise AssertionError("expected rejection")


def test_git_status_or_commit_drift_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/a.md").write_text("a", encoding="ascii")
    (tmp_path / "docs/b.md").write_text("b", encoding="ascii")
    first = b"?? docs/a.md\0"
    second = b"?? docs/a.md\0?? docs/b.md\0"
    _rejected(
        lambda: build_manifest(
            tmp_path, command_runner=DriftingGit([first, second])
        )
    )
    _rejected(
        lambda: build_manifest(
            tmp_path,
            command_runner=DriftingGit(
                [first, first], [COMMIT.encode(), ("b" * 40).encode()]
            ),
        )
    )


class MutatingGit:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.status_calls = 0

    def __call__(self, argv, root: Path) -> bytes:
        command = tuple(argv)
        if command == ("git", "rev-parse", "HEAD"):
            return COMMIT.encode()
        if command == ("git", "branch", "--show-current"):
            return b""
        if command[-1] == "--untracked-files=all":
            self.status_calls += 1
            if self.status_calls == 2:
                self.path.write_text("changed", encoding="ascii")
            return b"?? docs/a.md\0"
        raise AssertionError(command)


def test_file_byte_drift_between_passes_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    path = tmp_path / "docs/a.md"
    path.write_text("first", encoding="ascii")
    _rejected(lambda: build_manifest(tmp_path, command_runner=MutatingGit(path)))


def test_every_real_manifest_file_has_review_coverage() -> None:
    root = Path(__file__).parents[1]
    manifest = _real_manifest(root)
    assert manifest["file_count"] == len(manifest["files"])
    assert manifest["review_sections"] == list(REVIEW_SECTIONS)
    covered = set()
    for item in manifest["files"]:
        sections = item["review_sections"]
        assert sections
        assert set(sections) <= set(REVIEW_SECTIONS)
        covered.update(sections)
    assert covered == set(REVIEW_SECTIONS)


def test_root_security_inputs_receive_complete_review_coverage() -> None:
    root = Path(__file__).parents[1]
    manifest = _real_manifest(root)
    entries = {item["path"]: item for item in manifest["files"]}
    for path in (".grype.yaml", "Dockerfile"):
        assert entries[path]["review_sections"] == list(REVIEW_SECTIONS)


def test_known_secret_pattern_hits_are_exact_negative_fixtures() -> None:
    root = Path(__file__).parents[1]
    manifest = _real_manifest(root)
    marker = b"-----BEGIN " + b"PRIVATE KEY-----"
    hits = {
        item["path"]
        for item in manifest["files"]
        if marker in (root / item["path"]).read_bytes()
    }
    assert hits == {
        "tests/test_lq304_research_worker_staging_evidence.py",
        "tests/test_operational_release_bundle.py",
    }


def test_roadmap_links_reaudit_and_keeps_next_step_non_mutating() -> None:
    root = Path(__file__).parents[1]
    roadmap = (root / "docs/technical-status-and-roadmap.md").read_text(
        encoding="utf-8"
    )
    assert "- LQ-424 pre-staging manifest read-only reaudit:" in roadmap
    assert "`docs/lq-424-pre-staging-manifest-read-only-reaudit.md`" in roadmap
    assert "nächster Slice LQ-425" in roadmap
