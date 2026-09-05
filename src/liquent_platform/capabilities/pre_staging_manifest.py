"""Render one deterministic, read-only manifest of the uncommitted file scope."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
from typing import Callable, NoReturn, Sequence


SCHEMA_VERSION = 1
REVIEW_SECTIONS = (
    "identity_authority",
    "release_control_plane",
    "research_jobs_worker",
    "staging_recovery",
    "runtime_cleanup_lineage",
    "volume_disposition_deletion",
    "integration_preflight",
)
ALLOWED_PREFIXES = ("docs/", "operations/", "src/", "tests/", "tools/")
ALLOWED_FILES = {".grype.yaml", "Dockerfile", "pyproject.toml"}
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
SLICE_RE = re.compile(r"(?:lq-|test_lq)([0-9]{3})(?:-|_)")


class PreStagingManifestRejected(Exception):
    """One detail-limited manifest rejection."""


class PreStagingManifestUnstable(PreStagingManifestRejected):
    """Internal classification for source drift during the double snapshot."""


def _reject() -> NoReturn:
    raise PreStagingManifestRejected("pre-staging manifest rejected")


def _unstable() -> NoReturn:
    raise PreStagingManifestUnstable("pre-staging manifest rejected")


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


CommandRunner = Callable[[Sequence[str], Path], bytes]


def _command(argv: Sequence[str], source_root: Path) -> bytes:
    try:
        return subprocess.run(
            list(argv),
            cwd=source_root,
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        _reject()


def _slice_section(number: int) -> str | None:
    if 183 <= number <= 232:
        return REVIEW_SECTIONS[0]
    if 234 <= number <= 288:
        return REVIEW_SECTIONS[1]
    if 289 <= number <= 304:
        return REVIEW_SECTIONS[2]
    if 305 <= number <= 328:
        return REVIEW_SECTIONS[3]
    if 329 <= number <= 387:
        return REVIEW_SECTIONS[4]
    if 388 <= number <= 410:
        return REVIEW_SECTIONS[5]
    if 411 <= number <= 423:
        return REVIEW_SECTIONS[6]
    return None


def _review_sections(path: str) -> list[str]:
    match = SLICE_RE.search(PurePosixPath(path).name)
    if match:
        section = _slice_section(int(match.group(1)))
        if section is not None:
            return [section]

    lowered = path.lower()
    if "controlled_release_preflight" in lowered or "pre_staging_manifest" in lowered:
        return [REVIEW_SECTIONS[6]]
    rules = (
        ("volume", REVIEW_SECTIONS[5]),
        ("disposable_postgres", REVIEW_SECTIONS[4]),
        ("runtime_cleanup", REVIEW_SECTIONS[4]),
        ("release_publication", REVIEW_SECTIONS[1]),
        ("release_", REVIEW_SECTIONS[1]),
        ("research_worker", REVIEW_SECTIONS[2]),
        ("research_job", REVIEW_SECTIONS[2]),
        ("staging", REVIEW_SECTIONS[3]),
        ("artifact_probe", REVIEW_SECTIONS[3]),
        ("rollback", REVIEW_SECTIONS[3]),
        ("oidc", REVIEW_SECTIONS[0]),
        ("membership", REVIEW_SECTIONS[0]),
        ("identity", REVIEW_SECTIONS[0]),
    )
    matches = sorted({section for token, section in rules if token in lowered})
    return matches or list(REVIEW_SECTIONS)


def _records(value: bytes) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for raw in value.split(b"\0"):
        if not raw:
            continue
        if len(raw) < 4 or raw[2:3] != b" ":
            _reject()
        code = raw[:2]
        try:
            path = raw[3:].decode("utf-8")
        except UnicodeDecodeError:
            _reject()
        if code == b"??":
            status_name = "untracked"
        elif code[:1] == b" " and code[1:] == b"M":
            status_name = "modified"
        else:
            _reject()
        result.append((path, status_name))
    if len({path for path, _ in result}) != len(result):
        _reject()
    return sorted(result)


def _file_entry(source_root: Path, relative: str, status_name: str) -> dict[str, object]:
    pure = PurePosixPath(relative)
    if (
        not relative
        or relative.startswith("/")
        or ".." in pure.parts
        or str(pure) != relative
        or (
            relative not in ALLOWED_FILES
            and not any(relative.startswith(prefix) for prefix in ALLOWED_PREFIXES)
        )
    ):
        _reject()
    path = source_root.joinpath(*pure.parts)
    try:
        parent = source_root
        for part in pure.parts[:-1]:
            parent = parent / part
            parent_metadata = parent.lstat()
            if parent.is_symlink() or not stat.S_ISDIR(parent_metadata.st_mode):
                _reject()
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                _reject()
            chunks: list[bytes] = []
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            value = b"".join(chunks)
        finally:
            os.close(descriptor)
    except PreStagingManifestRejected:
        raise
    except OSError:
        _reject()
    return {
        "mode": format(stat.S_IMODE(metadata.st_mode), "04o"),
        "path": relative,
        "review_sections": _review_sections(relative),
        "sha256": hashlib.sha256(value).hexdigest(),
        "size": len(value),
        "status": status_name,
    }


def build_manifest(
    source_root: Path,
    *,
    command_runner: CommandRunner = _command,
) -> dict[str, object]:
    root = source_root.absolute()
    try:
        if root.is_symlink() or not root.is_dir():
            _reject()
        first_git = _git_snapshot(root, command_runner)
    except PreStagingManifestRejected:
        raise
    except (OSError, UnicodeError):
        _reject()
    commit, branch, status = first_git
    records = _records(status)
    first_files = [_file_entry(root, path, status_name) for path, status_name in records]
    if not first_files:
        _reject()
    try:
        second_git = _git_snapshot(root, command_runner)
        second_files = [
            _file_entry(root, path, status_name) for path, status_name in records
        ]
    except PreStagingManifestRejected:
        raise
    except OSError:
        _reject()
    if second_git != first_git or second_files != first_files:
        _unstable()
    return {
        "base_commit": commit,
        "branch": branch or None,
        "commit_authorized": False,
        "deployment_authorized": False,
        "file_count": len(first_files),
        "files": first_files,
        "publishing_authorized": False,
        "review_sections": list(REVIEW_SECTIONS),
        "schema_version": SCHEMA_VERSION,
        "staging_authorized": False,
    }


def _git_snapshot(
    root: Path, command_runner: CommandRunner
) -> tuple[str, str, bytes]:
    try:
        commit = command_runner(("git", "rev-parse", "HEAD"), root).decode(
            "ascii"
        ).strip()
        branch = command_runner(("git", "branch", "--show-current"), root).decode(
            "utf-8"
        ).strip()
        status = command_runner(
            (
                "git",
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
            ),
            root,
        )
    except PreStagingManifestRejected:
        raise
    except (OSError, UnicodeError):
        _reject()
    if not COMMIT_RE.fullmatch(commit) or "\n" in branch or "\x00" in branch:
        _reject()
    return commit, branch, status


def render_manifest(source_root: Path) -> bytes:
    return _canonical(build_manifest(source_root))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pre-staging-manifest")
    parser.add_argument("--source-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        value = render_manifest(args.source_root)
    except PreStagingManifestRejected:
        print(json.dumps({"error": "pre_staging_manifest_rejected"}))
        return 2
    os.write(1, value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
