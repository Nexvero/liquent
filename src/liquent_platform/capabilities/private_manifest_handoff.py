"""Atomically hand off one generated pre-staging manifest without overwrite."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import NoReturn, Sequence

from liquent_platform.capabilities.pre_staging_manifest import (
    PreStagingManifestRejected,
    PreStagingManifestUnstable,
    REVIEW_SECTIONS,
    render_manifest,
)


NAME_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?")
MANIFEST_KEYS = {
    "base_commit",
    "branch",
    "commit_authorized",
    "deployment_authorized",
    "file_count",
    "files",
    "publishing_authorized",
    "review_sections",
    "schema_version",
    "staging_authorized",
}


class ManifestHandoffUnavailable(Exception):
    """One detail-limited failure before a possible final bind."""


class ManifestHandoffUnknown(Exception):
    """One detail-limited failure after a possible final bind."""


def _unavailable() -> NoReturn:
    raise ManifestHandoffUnavailable("private manifest handoff unavailable")


def _unknown() -> NoReturn:
    raise ManifestHandoffUnknown("private manifest handoff outcome unknown")


@dataclass(frozen=True)
class ManifestHandoffResult:
    outcome: str
    filename: str | None = None
    manifest_sha256: str | None = None
    file_count: int | None = None


def _canonical_document(value: bytes) -> tuple[str, int]:
    try:
        document = json.loads(value)
    except (UnicodeError, json.JSONDecodeError):
        _unavailable()
    if (
        not isinstance(document, dict)
        or set(document) != MANIFEST_KEYS
        or document.get("schema_version") != 1
        or any(
            document.get(key) is not False
            for key in (
                "staging_authorized",
                "commit_authorized",
                "publishing_authorized",
                "deployment_authorized",
            )
        )
    ):
        _unavailable()
    count = document.get("file_count")
    files = document.get("files")
    if (
        isinstance(count, bool)
        or not isinstance(count, int)
        or count < 1
        or not isinstance(files, list)
        or len(files) != count
        or document.get("review_sections") != list(REVIEW_SECTIONS)
    ):
        _unavailable()
    canonical = (
        json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")
    if canonical != value:
        _unavailable()
    return hashlib.sha256(value).hexdigest(), count


def _safe_directory(path: Path, *, mode: int | None = None) -> Path:
    absolute = path.absolute()
    try:
        current = Path(absolute.anchor)
        for part in absolute.parts[1:]:
            current = current / part
            metadata = current.lstat()
            if current.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
                _unavailable()
        metadata = absolute.stat()
        if metadata.st_uid != os.geteuid():
            _unavailable()
        if mode is not None and stat.S_IMODE(metadata.st_mode) != mode:
            _unavailable()
    except (ManifestHandoffUnavailable, ManifestHandoffUnknown):
        raise
    except OSError:
        _unavailable()
    return absolute


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _write_all(descriptor: int, value: bytes) -> None:
    offset = 0
    while offset < len(value):
        written = os.write(descriptor, value[offset:])
        if written < 1:
            _unavailable()
        offset += written


def _read_all(descriptor: int) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while True:
        chunk = os.read(descriptor, 1024 * 1024)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _verify_descriptor(descriptor: int, expected: bytes) -> None:
    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_uid != os.geteuid()
        or metadata.st_size != len(expected)
        or _read_all(descriptor) != expected
    ):
        _unavailable()


def _sync_directory(root: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(root, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def handoff_manifest(
    source_root: Path,
    target_root: Path,
    handoff_name: str,
) -> ManifestHandoffResult:
    if not isinstance(handoff_name, str) or not NAME_RE.fullmatch(handoff_name):
        _unavailable()
    source = _safe_directory(source_root)
    target = _safe_directory(target_root, mode=0o700)
    if _inside(target, source) or _inside(source, target):
        _unavailable()
    filename = handoff_name + ".json"
    final = target / filename
    if os.path.lexists(final):
        return ManifestHandoffResult("target_not_absent")

    try:
        manifest = render_manifest(source)
    except PreStagingManifestUnstable:
        return ManifestHandoffResult("source_not_stable")
    except PreStagingManifestRejected:
        _unavailable()
    digest, count = _canonical_document(manifest)

    temporary: Path | None = None
    descriptor: int | None = None
    linked = False
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{handoff_name}-", suffix=".tmp", dir=target
        )
        temporary = Path(temporary_name)
        os.fchmod(descriptor, 0o600)
        _write_all(descriptor, manifest)
        os.fsync(descriptor)
        _verify_descriptor(descriptor, manifest)
        if os.path.lexists(final):
            return ManifestHandoffResult("target_not_absent")
        try:
            os.link(temporary, final, follow_symlinks=False)
            linked = True
        except FileExistsError:
            return ManifestHandoffResult("target_not_absent")
        _sync_directory(target)
        final_descriptor = os.open(
            final, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            _verify_descriptor(final_descriptor, manifest)
        finally:
            os.close(final_descriptor)
        temporary.unlink()
        temporary = None
        _sync_directory(target)
    except ManifestHandoffUnavailable:
        if linked:
            _unknown()
        raise
    except OSError:
        if linked:
            _unknown()
        _unavailable()
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if temporary is not None and not linked:
            try:
                temporary.unlink()
            except OSError:
                pass
    return ManifestHandoffResult(
        "manifest_handed_off", filename, digest, count
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="private-manifest-handoff")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--handoff-name", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = handoff_manifest(
            args.source_root, args.target_root, args.handoff_name
        )
    except ManifestHandoffUnknown:
        print(json.dumps({"error": "manifest_handoff_outcome_unknown"}))
        return 4
    except ManifestHandoffUnavailable:
        print(json.dumps({"error": "manifest_handoff_unavailable"}))
        return 2
    if result.outcome != "manifest_handed_off":
        print(json.dumps({"outcome": result.outcome}))
        return 3
    print(
        json.dumps(
            {
                "commit_authorized": False,
                "file_count": result.file_count,
                "filename": result.filename,
                "manifest_sha256": result.manifest_sha256,
                "outcome": result.outcome,
                "staging_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
