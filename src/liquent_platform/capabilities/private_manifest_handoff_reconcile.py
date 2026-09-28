"""Read-only reconciliation of one private manifest handoff name."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import stat
from typing import NoReturn, Sequence

from liquent_platform.capabilities.private_manifest_handoff import (
    ManifestHandoffUnavailable,
    NAME_RE,
    _canonical_document,
    _safe_directory,
)


class ManifestReconciliationUnavailable(Exception):
    """One detail-limited reconciliation failure."""


def _unavailable() -> NoReturn:
    raise ManifestReconciliationUnavailable(
        "private manifest handoff reconciliation unavailable"
    )


@dataclass(frozen=True)
class ManifestReconciliationResult:
    outcome: str
    filename: str | None = None
    manifest_sha256: str | None = None
    file_count: int | None = None
    temporary_present: bool = False


@dataclass(frozen=True)
class _ObservedManifest:
    digest: str
    file_count: int
    device: int
    inode: int


def _observe(path: Path) -> _ObservedManifest | None:
    if not os.path.lexists(path):
        return None
    try:
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            return None
        descriptor = os.open(
            path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or stat.S_IMODE(opened.st_mode) != 0o600
                or opened.st_uid != os.geteuid()
            ):
                return None
            chunks: list[bytes] = []
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            value = b"".join(chunks)
            digest, count = _canonical_document(value)
            return _ObservedManifest(
                digest, count, opened.st_dev, opened.st_ino
            )
        finally:
            os.close(descriptor)
    except Exception as error:
        if isinstance(error, ManifestHandoffUnavailable):
            return None
        if isinstance(error, OSError):
            _unavailable()
        raise


def reconcile_manifest_handoff(
    target_root: Path, handoff_name: str
) -> ManifestReconciliationResult:
    if not isinstance(handoff_name, str) or not NAME_RE.fullmatch(handoff_name):
        _unavailable()
    try:
        target = _safe_directory(target_root, mode=0o700)
        filename = handoff_name + ".json"
        final_path = target / filename
        temporary_re = re.compile(
            rf"\.{re.escape(handoff_name)}-[A-Za-z0-9_-]+\.tmp"
        )
        temporary_paths = sorted(
            path
            for path in target.iterdir()
            if temporary_re.fullmatch(path.name)
        )
    except ManifestReconciliationUnavailable:
        raise
    except Exception as error:
        if isinstance(error, ManifestHandoffUnavailable) or isinstance(error, OSError):
            _unavailable()
        raise

    if len(temporary_paths) > 1:
        return ManifestReconciliationResult("manifest_handoff_conflict")
    final = _observe(final_path)
    temporary = _observe(temporary_paths[0]) if temporary_paths else None

    if os.path.lexists(final_path) and final is None:
        return ManifestReconciliationResult("manifest_handoff_conflict")
    if temporary_paths and temporary is None:
        return ManifestReconciliationResult("manifest_handoff_conflict")
    if final is None and temporary is None:
        return ManifestReconciliationResult("manifest_absent")
    if final is None and temporary is not None:
        return ManifestReconciliationResult(
            "manifest_temporary_only",
            manifest_sha256=temporary.digest,
            file_count=temporary.file_count,
            temporary_present=True,
        )
    if final is not None and temporary is None:
        return ManifestReconciliationResult(
            "manifest_handed_off",
            filename=filename,
            manifest_sha256=final.digest,
            file_count=final.file_count,
        )
    assert final is not None and temporary is not None
    if (
        final.device != temporary.device
        or final.inode != temporary.inode
        or final.digest != temporary.digest
        or final.file_count != temporary.file_count
    ):
        return ManifestReconciliationResult("manifest_handoff_conflict")
    return ManifestReconciliationResult(
        "manifest_handed_off_pending_cleanup",
        filename=filename,
        manifest_sha256=final.digest,
        file_count=final.file_count,
        temporary_present=True,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="private-manifest-handoff-reconcile")
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--handoff-name", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = reconcile_manifest_handoff(args.target_root, args.handoff_name)
    except ManifestReconciliationUnavailable:
        print(json.dumps({"error": "manifest_handoff_reconciliation_unavailable"}))
        return 2
    value: dict[str, object] = {
        "commit_authorized": False,
        "outcome": result.outcome,
        "staging_authorized": False,
        "temporary_present": result.temporary_present,
    }
    if result.filename is not None:
        value["filename"] = result.filename
    if result.manifest_sha256 is not None:
        value["manifest_sha256"] = result.manifest_sha256
    if result.file_count is not None:
        value["file_count"] = result.file_count
    print(json.dumps(value, sort_keys=True))
    return 0 if result.outcome == "manifest_handed_off" else 3


if __name__ == "__main__":
    raise SystemExit(main())
