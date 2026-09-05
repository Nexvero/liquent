#!/usr/bin/env python3
"""Remove one proven redundant private manifest handoff temporary name."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import stat
from typing import NoReturn, Sequence

from tools.private_manifest_handoff import (
    ManifestHandoffUnavailable,
    NAME_RE,
    _canonical_document,
    _safe_directory,
)
from tools.private_manifest_handoff_reconcile import (
    ManifestReconciliationUnavailable,
    reconcile_manifest_handoff,
)


class ManifestCleanupUnavailable(Exception):
    """One detail-limited failure before possible temporary-name removal."""


class ManifestCleanupUnknown(Exception):
    """One detail-limited failure after possible temporary-name removal."""


def _unavailable() -> NoReturn:
    raise ManifestCleanupUnavailable("private manifest handoff cleanup unavailable")


def _unknown() -> NoReturn:
    raise ManifestCleanupUnknown("private manifest handoff cleanup outcome unknown")


@dataclass(frozen=True)
class ManifestCleanupResult:
    outcome: str
    observed_outcome: str
    filename: str | None = None
    manifest_sha256: str | None = None
    file_count: int | None = None


def _read_manifest(descriptor: int) -> tuple[str, int, os.stat_result] | None:
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_uid != os.geteuid()
        ):
            return None
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        digest, count = _canonical_document(b"".join(chunks))
        return digest, count, metadata
    except ManifestHandoffUnavailable:
        return None
    except OSError:
        _unavailable()


def _matching_temporary_names(target: Path, handoff_name: str) -> list[str]:
    pattern = re.compile(rf"\.{re.escape(handoff_name)}-[A-Za-z0-9_-]+\.tmp")
    try:
        return sorted(path.name for path in target.iterdir() if pattern.fullmatch(path.name))
    except OSError:
        _unavailable()


def cleanup_manifest_handoff(
    target_root: Path, handoff_name: str
) -> ManifestCleanupResult:
    if not isinstance(handoff_name, str) or not NAME_RE.fullmatch(handoff_name):
        _unavailable()
    try:
        target = _safe_directory(target_root, mode=0o700)
        observed = reconcile_manifest_handoff(target, handoff_name)
    except (ManifestHandoffUnavailable, ManifestReconciliationUnavailable):
        _unavailable()
    if observed.outcome != "manifest_handed_off_pending_cleanup":
        return ManifestCleanupResult("cleanup_not_applicable", observed.outcome)

    filename = handoff_name + ".json"
    temporary_names = _matching_temporary_names(target, handoff_name)
    if len(temporary_names) != 1:
        return ManifestCleanupResult(
            "manifest_handoff_cleanup_conflict", "manifest_handoff_conflict"
        )
    temporary_name = temporary_names[0]
    directory_descriptor: int | None = None
    final_descriptor: int | None = None
    temporary_descriptor: int | None = None
    removed = False
    try:
        directory_descriptor = os.open(
            target,
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0),
        )
        directory_metadata = os.fstat(directory_descriptor)
        target_metadata = target.stat()
        if (
            directory_metadata.st_dev != target_metadata.st_dev
            or directory_metadata.st_ino != target_metadata.st_ino
            or directory_metadata.st_uid != os.geteuid()
            or stat.S_IMODE(directory_metadata.st_mode) != 0o700
        ):
            return ManifestCleanupResult(
                "manifest_handoff_cleanup_conflict", "manifest_handoff_conflict"
            )
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        final_descriptor = os.open(filename, flags, dir_fd=directory_descriptor)
        temporary_descriptor = os.open(
            temporary_name, flags, dir_fd=directory_descriptor
        )
        final = _read_manifest(final_descriptor)
        temporary = _read_manifest(temporary_descriptor)
        if final is None or temporary is None:
            return ManifestCleanupResult(
                "manifest_handoff_cleanup_conflict", "manifest_handoff_conflict"
            )
        final_digest, final_count, final_metadata = final
        temporary_digest, temporary_count, temporary_metadata = temporary
        current_final = os.stat(filename, dir_fd=directory_descriptor, follow_symlinks=False)
        current_temporary = os.stat(
            temporary_name, dir_fd=directory_descriptor, follow_symlinks=False
        )
        identity = (final_metadata.st_dev, final_metadata.st_ino)
        if (
            identity != (temporary_metadata.st_dev, temporary_metadata.st_ino)
            or identity != (current_final.st_dev, current_final.st_ino)
            or identity != (current_temporary.st_dev, current_temporary.st_ino)
            or final_digest != temporary_digest
            or final_count != temporary_count
        ):
            return ManifestCleanupResult(
                "manifest_handoff_cleanup_conflict", "manifest_handoff_conflict"
            )
        os.unlink(temporary_name, dir_fd=directory_descriptor)
        removed = True
        os.fsync(directory_descriptor)
        current_final = os.stat(filename, dir_fd=directory_descriptor, follow_symlinks=False)
        if identity != (current_final.st_dev, current_final.st_ino):
            _unknown()
        if _matching_temporary_names(target, handoff_name):
            _unknown()
        return ManifestCleanupResult(
            "manifest_handoff_cleanup_completed",
            "manifest_handed_off",
            filename,
            final_digest,
            final_count,
        )
    except ManifestCleanupUnknown:
        raise
    except ManifestCleanupUnavailable:
        if removed:
            _unknown()
        raise
    except OSError:
        if removed:
            _unknown()
        _unavailable()
    finally:
        for descriptor in (temporary_descriptor, final_descriptor, directory_descriptor):
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="private-manifest-handoff-cleanup")
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--handoff-name", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = cleanup_manifest_handoff(args.target_root, args.handoff_name)
    except ManifestCleanupUnknown:
        print(json.dumps({"error": "manifest_handoff_cleanup_outcome_unknown"}))
        return 4
    except ManifestCleanupUnavailable:
        print(json.dumps({"error": "manifest_handoff_cleanup_unavailable"}))
        return 2
    value: dict[str, object] = {
        "commit_authorized": False,
        "observed_outcome": result.observed_outcome,
        "outcome": result.outcome,
        "staging_authorized": False,
    }
    if result.filename is not None:
        value["filename"] = result.filename
    if result.manifest_sha256 is not None:
        value["manifest_sha256"] = result.manifest_sha256
    if result.file_count is not None:
        value["file_count"] = result.file_count
    print(json.dumps(value, sort_keys=True))
    return 0 if result.outcome == "manifest_handoff_cleanup_completed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
