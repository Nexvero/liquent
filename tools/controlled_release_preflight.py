#!/usr/bin/env python3
"""Atomically coordinate one fixed, non-publishing release preflight."""

from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import tempfile
from typing import Iterable, Iterator, Mapping, NoReturn, Protocol


PHASES = (
    "runtime",
    "source",
    "normal_tests",
    "postgres_tests",
    "distributions",
    "wheel",
    "entrypoints",
    "sdist",
    "final_diff",
    "bundle",
)
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
DIGEST_RE = re.compile(r"[0-9a-f]{64}")
RECEIPT_KEYS = {
    "schema_version",
    "phase",
    "status",
    "source_commit",
    "facts_sha256",
}
EVIDENCE_NAME = "controlled-preflight.json"
MAX_GATE_RECEIPT_BYTES = 1024
MAX_CONTROLLED_EVIDENCE_BYTES = 64 * 1024
WORKSPACE_INVENTORY = {
    "artifacts": "directory",
    "bundle": "directory",
    EVIDENCE_NAME: "file",
    "installed-wheel": "directory",
    "sdist-wheel-roundtrip": "directory",
}
PHASE_OUTPUT_DIRECTORIES = {
    "distributions": "artifacts",
    "entrypoints": "installed-wheel",
    "sdist": "sdist-wheel-roundtrip",
    "bundle": "bundle",
}


class ControlledPreflightRejected(Exception):
    """One detail-limited preflight rejection."""


def _reject() -> NoReturn:
    raise ControlledPreflightRejected("controlled release preflight rejected")


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _unlink_created_workspace_evidence(
    directory_descriptor: int,
    expected_identity: tuple[int, int] | None,
    expected_workspace_identity: tuple[int, int],
) -> None:
    if expected_identity is None:
        return
    try:
        parent = os.fstat(directory_descriptor)
        if (
            (parent.st_dev, parent.st_ino) != expected_workspace_identity
            or stat.S_IMODE(parent.st_mode) != 0o700
            or parent.st_uid != os.getuid()
        ):
            return
        current = os.stat(
            EVIDENCE_NAME,
            dir_fd=directory_descriptor,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(current.st_mode)
            or (current.st_dev, current.st_ino) != expected_identity
        ):
            return
        os.unlink(EVIDENCE_NAME, dir_fd=directory_descriptor)
        os.fsync(directory_descriptor)
        parent_after = os.fstat(directory_descriptor)
        if (
            (parent_after.st_dev, parent_after.st_ino)
            != expected_workspace_identity
            or stat.S_IMODE(parent_after.st_mode) != 0o700
            or parent_after.st_uid != os.getuid()
        ):
            return
    except OSError:
        return


def _write_private_workspace_evidence(workspace: Path, payload: bytes) -> Path:
    return _write_private_workspace_evidence_with_identity(workspace, payload)[0]


def _write_private_workspace_evidence_with_identity(
    workspace: Path,
    payload: bytes,
    *,
    expected_workspace_identity: tuple[int, int] | None = None,
) -> tuple[Path, tuple[int, int]]:
    directory_descriptor: int | None = None
    evidence_descriptor: int | None = None
    created = False
    created_identity: tuple[int, int] | None = None
    try:
        directory_descriptor = os.open(
            workspace, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        directory_metadata = os.fstat(directory_descriptor)
        if (
            not stat.S_ISDIR(directory_metadata.st_mode)
            or stat.S_IMODE(directory_metadata.st_mode) != 0o700
            or directory_metadata.st_uid != os.getuid()
            or (
                expected_workspace_identity is not None
                and (directory_metadata.st_dev, directory_metadata.st_ino)
                != expected_workspace_identity
            )
            or not payload
            or len(payload) > MAX_CONTROLLED_EVIDENCE_BYTES
        ):
            _reject()
        evidence_descriptor = os.open(
            EVIDENCE_NAME,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory_descriptor,
        )
        created = True
        os.fchmod(evidence_descriptor, 0o600)
        created_metadata = os.fstat(evidence_descriptor)
        if (
            not stat.S_ISREG(created_metadata.st_mode)
            or stat.S_IMODE(created_metadata.st_mode) != 0o600
            or created_metadata.st_uid != os.getuid()
            or created_metadata.st_nlink != 1
            or created_metadata.st_size != 0
        ):
            _reject()
        created_identity = (created_metadata.st_dev, created_metadata.st_ino)
        view = memoryview(payload)
        while view:
            written = os.write(evidence_descriptor, view)
            if written < 1:
                _reject()
            view = view[written:]
        os.fsync(evidence_descriptor)
        evidence_metadata = os.fstat(evidence_descriptor)
        if (
            not stat.S_ISREG(evidence_metadata.st_mode)
            or stat.S_IMODE(evidence_metadata.st_mode) != 0o600
            or evidence_metadata.st_uid != os.getuid()
            or evidence_metadata.st_nlink != 1
            or evidence_metadata.st_size != len(payload)
        ):
            _reject()
        os.fsync(directory_descriptor)
        after = os.fstat(directory_descriptor)
        if (after.st_dev, after.st_ino) != (
            directory_metadata.st_dev,
            directory_metadata.st_ino,
        ) or (
            expected_workspace_identity is not None
            and (after.st_dev, after.st_ino) != expected_workspace_identity
        ):
            _reject()
        return (
            workspace / EVIDENCE_NAME,
            (evidence_metadata.st_dev, evidence_metadata.st_ino),
        )
    except ControlledPreflightRejected:
        if created and directory_descriptor is not None:
            _unlink_created_workspace_evidence(
                directory_descriptor,
                created_identity,
                (directory_metadata.st_dev, directory_metadata.st_ino),
            )
        raise
    except OSError:
        if created and directory_descriptor is not None:
            _unlink_created_workspace_evidence(
                directory_descriptor,
                created_identity,
                (directory_metadata.st_dev, directory_metadata.st_ino),
            )
        _reject()
    finally:
        if evidence_descriptor is not None:
            os.close(evidence_descriptor)
        if directory_descriptor is not None:
            os.close(directory_descriptor)


def _verify_private_workspace_evidence(
    workspace: Path,
    expected: bytes,
    expected_identity: tuple[int, int] | None = None,
    expected_workspace_identity: tuple[int, int] | None = None,
) -> tuple[int, int]:
    directory_descriptor: int | None = None
    evidence_descriptor: int | None = None
    try:
        directory_descriptor = os.open(
            workspace, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        directory_metadata = os.fstat(directory_descriptor)
        if (
            not stat.S_ISDIR(directory_metadata.st_mode)
            or stat.S_IMODE(directory_metadata.st_mode) != 0o700
            or directory_metadata.st_uid != os.getuid()
            or (
                expected_workspace_identity is not None
                and (directory_metadata.st_dev, directory_metadata.st_ino)
                != expected_workspace_identity
            )
            or not expected
            or len(expected) > MAX_CONTROLLED_EVIDENCE_BYTES
        ):
            _reject()
        evidence_descriptor = os.open(
            EVIDENCE_NAME,
            os.O_RDONLY | os.O_NOFOLLOW,
            dir_fd=directory_descriptor,
        )
        before = os.fstat(evidence_descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_uid != os.getuid()
            or before.st_nlink != 1
            or before.st_size != len(expected)
            or (
                expected_identity is not None
                and (before.st_dev, before.st_ino) != expected_identity
            )
        ):
            _reject()
        payload = b""
        while chunk := os.read(evidence_descriptor, MAX_CONTROLLED_EVIDENCE_BYTES + 1):
            payload += chunk
            if len(payload) > MAX_CONTROLLED_EVIDENCE_BYTES:
                _reject()
        after = os.fstat(evidence_descriptor)
        directory_after = os.fstat(directory_descriptor)
        if (
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            or payload != expected
            or (directory_after.st_dev, directory_after.st_ino)
            != (directory_metadata.st_dev, directory_metadata.st_ino)
            or (
                expected_workspace_identity is not None
                and (directory_after.st_dev, directory_after.st_ino)
                != expected_workspace_identity
            )
        ):
            _reject()
        return after.st_dev, after.st_ino
    except ControlledPreflightRejected:
        raise
    except OSError:
        _reject()
    finally:
        if evidence_descriptor is not None:
            os.close(evidence_descriptor)
        if directory_descriptor is not None:
            os.close(directory_descriptor)


def _private_workspace_identity(workspace: Path) -> tuple[int, int]:
    descriptor: int | None = None
    try:
        descriptor = os.open(
            workspace, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o700
            or metadata.st_uid != os.getuid()
        ):
            _reject()
        return metadata.st_dev, metadata.st_ino
    except ControlledPreflightRejected:
        raise
    except OSError:
        _reject()
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _close_descriptors_or_reject(descriptors: Iterable[int]) -> None:
    close_failed = False
    for descriptor in descriptors:
        try:
            os.close(descriptor)
        except OSError:
            close_failed = True
    if close_failed:
        _reject()


def _is_filesystem_identity(value: object) -> bool:
    return (
        type(value) is tuple
        and len(value) == 2
        and all(type(item) is int and item >= 0 for item in value)
    )


def _private_workspace_child_identity(
    workspace: Path, workspace_identity: tuple[int, int], name: str
) -> tuple[int, int]:
    descriptor: int | None = None
    child_descriptor: int | None = None
    try:
        if (
            not _is_filesystem_identity(workspace_identity)
            or type(name) is not str
            or name not in set(PHASE_OUTPUT_DIRECTORIES.values())
        ):
            _reject()
        descriptor = os.open(
            workspace, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        parent = os.fstat(descriptor)
        child_descriptor = os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=descriptor,
        )
        child = os.fstat(child_descriptor)
        namespace_child = os.stat(
            name, dir_fd=descriptor, follow_symlinks=False
        )
        terminal_child = os.fstat(child_descriptor)
        terminal_namespace_child = os.stat(
            name, dir_fd=descriptor, follow_symlinks=False
        )
        terminal_parent = os.fstat(descriptor)
        if (
            (parent.st_dev, parent.st_ino) != workspace_identity
            or (terminal_parent.st_dev, terminal_parent.st_ino)
            != workspace_identity
            or stat.S_IMODE(parent.st_mode) != 0o700
            or stat.S_IMODE(terminal_parent.st_mode) != 0o700
            or parent.st_uid != os.getuid()
            or terminal_parent.st_uid != os.getuid()
            or not stat.S_ISDIR(child.st_mode)
            or stat.S_IMODE(child.st_mode) != 0o700
            or child.st_uid != os.getuid()
            or not stat.S_ISDIR(namespace_child.st_mode)
            or stat.S_IMODE(namespace_child.st_mode) != 0o700
            or namespace_child.st_uid != os.getuid()
            or (namespace_child.st_dev, namespace_child.st_ino)
            != (child.st_dev, child.st_ino)
            or not stat.S_ISDIR(terminal_child.st_mode)
            or stat.S_IMODE(terminal_child.st_mode) != 0o700
            or terminal_child.st_uid != os.getuid()
            or (terminal_child.st_dev, terminal_child.st_ino)
            != (child.st_dev, child.st_ino)
            or not stat.S_ISDIR(terminal_namespace_child.st_mode)
            or stat.S_IMODE(terminal_namespace_child.st_mode) != 0o700
            or terminal_namespace_child.st_uid != os.getuid()
            or (
                terminal_namespace_child.st_dev,
                terminal_namespace_child.st_ino,
            )
            != (child.st_dev, child.st_ino)
        ):
            _reject()
        return child.st_dev, child.st_ino
    except ControlledPreflightRejected:
        raise
    except OSError:
        _reject()
    finally:
        _close_descriptors_or_reject(
            item
            for item in (child_descriptor, descriptor)
            if item is not None
        )


def _verify_intermediate_workspace_entries(
    workspace: Path,
    workspace_identity: tuple[int, int],
    expected_directory_identities: Mapping[str, tuple[int, int]],
) -> None:
    descriptor: int | None = None
    child_descriptors: dict[str, int] = {}
    try:
        expected = dict(expected_directory_identities)
        if (
            not _is_filesystem_identity(workspace_identity)
            or any(type(name) is not str for name in expected)
            or not set(expected).issubset(
                set(PHASE_OUTPUT_DIRECTORIES.values())
            )
            or any(
                not _is_filesystem_identity(identity)
                for identity in expected.values()
            )
            or len(set(expected.values())) != len(expected)
            or workspace_identity in expected.values()
        ):
            _reject()
        descriptor = os.open(
            workspace, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        root = os.fstat(descriptor)
        names = set(os.listdir(descriptor))
        if (
            (root.st_dev, root.st_ino) != workspace_identity
            or stat.S_IMODE(root.st_mode) != 0o700
            or root.st_uid != os.getuid()
            or names != set(expected)
        ):
            _reject()
        for name in sorted(names):
            child_descriptor = os.open(
                name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=descriptor,
            )
            child_descriptors[name] = child_descriptor
            child = os.fstat(child_descriptor)
            if (
                not stat.S_ISDIR(child.st_mode)
                or stat.S_IMODE(child.st_mode) != 0o700
                or child.st_uid != os.getuid()
                or (child.st_dev, child.st_ino)
                != expected[name]
            ):
                _reject()
        if set(os.listdir(descriptor)) != names:
            _reject()
        for name in sorted(names):
            namespace_child = os.stat(
                name, dir_fd=descriptor, follow_symlinks=False
            )
            retained_child = os.fstat(child_descriptors[name])
            if (
                not stat.S_ISDIR(namespace_child.st_mode)
                or stat.S_IMODE(namespace_child.st_mode) != 0o700
                or namespace_child.st_uid != os.getuid()
                or (namespace_child.st_dev, namespace_child.st_ino)
                != expected[name]
                or not stat.S_ISDIR(retained_child.st_mode)
                or stat.S_IMODE(retained_child.st_mode) != 0o700
                or retained_child.st_uid != os.getuid()
                or (retained_child.st_dev, retained_child.st_ino)
                != expected[name]
            ):
                _reject()
        if set(os.listdir(descriptor)) != names:
            _reject()
        terminal_root = os.fstat(descriptor)
        if (
            (terminal_root.st_dev, terminal_root.st_ino) != workspace_identity
            or stat.S_IMODE(terminal_root.st_mode) != 0o700
            or terminal_root.st_uid != os.getuid()
        ):
            _reject()
    except ControlledPreflightRejected:
        raise
    except OSError:
        _reject()
    finally:
        _close_descriptors_or_reject(
            item
            for item in (*child_descriptors.values(), descriptor)
            if item is not None
        )


def _verify_private_workspace_inventory(
    workspace: Path,
    workspace_identity: tuple[int, int],
    expected_directory_identities: Mapping[str, tuple[int, int]] | None = None,
    expected_evidence_identity: tuple[int, int] | None = None,
) -> None:
    descriptor: int | None = None
    try:
        descriptor = os.open(
            workspace, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        metadata = os.fstat(descriptor)
        if (
            (metadata.st_dev, metadata.st_ino) != workspace_identity
            or stat.S_IMODE(metadata.st_mode) != 0o700
            or metadata.st_uid != os.getuid()
            or set(os.listdir(descriptor)) != set(WORKSPACE_INVENTORY)
        ):
            _reject()
        for name, expected_type in WORKSPACE_INVENTORY.items():
            child = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if child.st_uid != os.getuid():
                _reject()
            if expected_type == "directory":
                if (
                    not stat.S_ISDIR(child.st_mode)
                    or stat.S_IMODE(child.st_mode) != 0o700
                    or (
                        expected_directory_identities is not None
                        and (child.st_dev, child.st_ino)
                        != expected_directory_identities.get(name)
                    )
                ):
                    _reject()
            elif (
                not stat.S_ISREG(child.st_mode)
                or stat.S_IMODE(child.st_mode) != 0o600
                or child.st_nlink != 1
                or child.st_size < 1
                or child.st_size > MAX_CONTROLLED_EVIDENCE_BYTES
                or (
                    expected_evidence_identity is not None
                    and (child.st_dev, child.st_ino) != expected_evidence_identity
                )
            ):
                _reject()
        after = os.fstat(descriptor)
        if (
            (after.st_dev, after.st_ino) != workspace_identity
            or set(os.listdir(descriptor)) != set(WORKSPACE_INVENTORY)
        ):
            _reject()
    except ControlledPreflightRejected:
        raise
    except OSError:
        _reject()
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _private_output_parent_identity(output: Path) -> tuple[int, int]:
    descriptor: int | None = None
    try:
        if output.name in {"", ".", ".."}:
            _reject()
        descriptor = os.open(
            output.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o700
            or metadata.st_uid != os.getuid()
        ):
            _reject()
        try:
            os.stat(output.name, dir_fd=descriptor, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            _reject()
        return metadata.st_dev, metadata.st_ino
    except ControlledPreflightRejected:
        raise
    except OSError:
        _reject()
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _verify_bound_child_directory_identities(
    workspace_descriptor: int,
    expected: Mapping[str, tuple[int, int]],
) -> None:
    if set(expected) != set(PHASE_OUTPUT_DIRECTORIES.values()):
        _reject()
    names = sorted(os.listdir(workspace_descriptor))
    if set(names) != set(WORKSPACE_INVENTORY):
        _reject()
    descriptors: list[tuple[int, tuple[int, int]]] = []
    try:
        for name, identity in sorted(expected.items()):
            child_descriptor = os.open(
                name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=workspace_descriptor,
            )
            descriptors.append((child_descriptor, identity))
            child = os.fstat(child_descriptor)
            if (
                not stat.S_ISDIR(child.st_mode)
                or stat.S_IMODE(child.st_mode) != 0o700
                or child.st_uid != os.getuid()
                or (child.st_dev, child.st_ino) != identity
            ):
                _reject()
        if sorted(os.listdir(workspace_descriptor)) != names:
            _reject()
        for child_descriptor, identity in descriptors:
            child = os.fstat(child_descriptor)
            if (
                (child.st_dev, child.st_ino) != identity
                or stat.S_IMODE(child.st_mode) != 0o700
                or child.st_uid != os.getuid()
            ):
                _reject()
    except ControlledPreflightRejected:
        raise
    except OSError:
        _reject()
    finally:
        for child_descriptor, _ in descriptors:
            os.close(child_descriptor)


def _rollback_private_workspace_publication(
    parent_descriptor: int,
    *,
    parent_identity: tuple[int, int],
    workspace_name: str,
    output_name: str,
    workspace_identity: tuple[int, int],
) -> bool:
    try:
        parent = os.fstat(parent_descriptor)
        if (
            (parent.st_dev, parent.st_ino) != parent_identity
            or parent.st_uid != os.getuid()
        ):
            return False
        try:
            os.stat(workspace_name, dir_fd=parent_descriptor, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            return False
        output = os.stat(
            output_name, dir_fd=parent_descriptor, follow_symlinks=False
        )
        if (
            not stat.S_ISDIR(output.st_mode)
            or (output.st_dev, output.st_ino) != workspace_identity
        ):
            return False
        os.rename(
            output_name,
            workspace_name,
            src_dir_fd=parent_descriptor,
            dst_dir_fd=parent_descriptor,
        )
        os.fsync(parent_descriptor)
        restored = os.stat(
            workspace_name, dir_fd=parent_descriptor, follow_symlinks=False
        )
        try:
            os.stat(output_name, dir_fd=parent_descriptor, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            return False
        parent_after = os.fstat(parent_descriptor)
        return (
            (restored.st_dev, restored.st_ino) == workspace_identity
            and (parent_after.st_dev, parent_after.st_ino) == parent_identity
            and parent_after.st_uid == os.getuid()
        )
    except OSError:
        return False


def _publish_private_workspace(
    workspace: Path,
    output: Path,
    *,
    parent_identity: tuple[int, int],
    workspace_identity: tuple[int, int],
    expected_directory_identities: Mapping[str, tuple[int, int]] | None = None,
    expected_evidence: bytes | None = None,
    expected_evidence_identity: tuple[int, int] | None = None,
) -> None:
    descriptor: int | None = None
    workspace_descriptor: int | None = None
    published_descriptor: int | None = None
    renamed = False
    try:
        if workspace.parent != output.parent:
            _reject()
        descriptor = os.open(
            output.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        parent = os.fstat(descriptor)
        if (
            (parent.st_dev, parent.st_ino) != parent_identity
            or stat.S_IMODE(parent.st_mode) != 0o700
            or parent.st_uid != os.getuid()
        ):
            _reject()
        try:
            os.stat(output.name, dir_fd=descriptor, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            _reject()
        workspace_metadata = os.stat(
            workspace.name, dir_fd=descriptor, follow_symlinks=False
        )
        if (
            not stat.S_ISDIR(workspace_metadata.st_mode)
            or stat.S_IMODE(workspace_metadata.st_mode) != 0o700
            or workspace_metadata.st_uid != os.getuid()
            or (workspace_metadata.st_dev, workspace_metadata.st_ino)
            != workspace_identity
        ):
            _reject()
        workspace_descriptor = os.open(
            workspace.name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=descriptor,
        )
        opened_workspace = os.fstat(workspace_descriptor)
        if (opened_workspace.st_dev, opened_workspace.st_ino) != workspace_identity:
            _reject()
        if expected_directory_identities is not None:
            _verify_bound_child_directory_identities(
                workspace_descriptor, expected_directory_identities
            )
        parent_before_commit = os.fstat(descriptor)
        source_before_commit = os.stat(
            workspace.name, dir_fd=descriptor, follow_symlinks=False
        )
        if (
            (parent_before_commit.st_dev, parent_before_commit.st_ino)
            != parent_identity
            or stat.S_IMODE(parent_before_commit.st_mode) != 0o700
            or parent_before_commit.st_uid != os.getuid()
            or not stat.S_ISDIR(source_before_commit.st_mode)
            or stat.S_IMODE(source_before_commit.st_mode) != 0o700
            or source_before_commit.st_uid != os.getuid()
            or (source_before_commit.st_dev, source_before_commit.st_ino)
            != workspace_identity
        ):
            _reject()
        try:
            os.stat(output.name, dir_fd=descriptor, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            _reject()
        os.rename(
            workspace.name,
            output.name,
            src_dir_fd=descriptor,
            dst_dir_fd=descriptor,
        )
        renamed = True
        os.fsync(descriptor)
        published_descriptor = os.open(
            output.name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=descriptor,
        )
        published = os.fstat(published_descriptor)
        if (
            (published.st_dev, published.st_ino) != workspace_identity
            or stat.S_IMODE(published.st_mode) != 0o700
            or published.st_uid != os.getuid()
        ):
            _reject()
        if expected_directory_identities is not None:
            _verify_bound_child_directory_identities(
                published_descriptor, expected_directory_identities
            )
        if expected_evidence is not None:
            _verify_private_workspace_evidence(
                output,
                expected_evidence,
                expected_identity=expected_evidence_identity,
                expected_workspace_identity=workspace_identity,
            )
            _verify_private_workspace_inventory(
                output,
                workspace_identity,
                expected_directory_identities=expected_directory_identities,
                expected_evidence_identity=expected_evidence_identity,
            )
        parent_after = os.fstat(descriptor)
        output_after = os.stat(
            output.name, dir_fd=descriptor, follow_symlinks=False
        )
        try:
            os.stat(workspace.name, dir_fd=descriptor, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            _reject()
        if (
            (parent_after.st_dev, parent_after.st_ino) != parent_identity
            or stat.S_IMODE(parent_after.st_mode) != 0o700
            or parent_after.st_uid != os.getuid()
            or not stat.S_ISDIR(output_after.st_mode)
            or stat.S_IMODE(output_after.st_mode) != 0o700
            or output_after.st_uid != os.getuid()
            or (output_after.st_dev, output_after.st_ino) != workspace_identity
        ):
            _reject()
    except ControlledPreflightRejected:
        if renamed and descriptor is not None:
            _rollback_private_workspace_publication(
                descriptor,
                parent_identity=parent_identity,
                workspace_name=workspace.name,
                output_name=output.name,
                workspace_identity=workspace_identity,
            )
        raise
    except OSError:
        if renamed and descriptor is not None:
            _rollback_private_workspace_publication(
                descriptor,
                parent_identity=parent_identity,
                workspace_name=workspace.name,
                output_name=output.name,
                workspace_identity=workspace_identity,
            )
        _reject()
    finally:
        if published_descriptor is not None:
            os.close(published_descriptor)
        if workspace_descriptor is not None:
            os.close(workspace_descriptor)
        if descriptor is not None:
            os.close(descriptor)


@dataclass(frozen=True)
class GateReceipt:
    phase: str
    source_commit: str
    facts_sha256: str

    @classmethod
    def parse(cls, value: bytes, expected_phase: str) -> "GateReceipt":
        if (
            not isinstance(value, bytes)
            or not value
            or len(value) > MAX_GATE_RECEIPT_BYTES
            or expected_phase not in PHASES
        ):
            _reject()
        try:
            document = json.loads(value)
        except (UnicodeError, json.JSONDecodeError):
            _reject()
        if not isinstance(document, dict) or set(document) != RECEIPT_KEYS:
            _reject()
        if (
            document.get("schema_version") != 1
            or document.get("phase") != expected_phase
            or document.get("status") != "passed"
        ):
            _reject()
        commit = document.get("source_commit")
        digest = document.get("facts_sha256")
        if (
            not isinstance(commit, str)
            or not COMMIT_RE.fullmatch(commit)
            or not isinstance(digest, str)
            or not DIGEST_RE.fullmatch(digest)
        ):
            _reject()
        if value != _canonical(document):
            _reject()
        return cls(expected_phase, commit, digest)


class BuildGate(Protocol):
    """Trusted phase adapter; it may write only below the private workspace."""

    def execute(self, workspace: Path) -> bytes:
        """Run the phase and return one canonical, phase-bound receipt."""


class ControlledReleasePreflight:
    """Run every required phase once and publish evidence only as one unit."""

    def __init__(self, gates: Mapping[str, BuildGate]) -> None:
        if set(gates) != set(PHASES):
            _reject()
        self._gates = dict(gates)

    def run(self, output_directory: Path) -> Path:
        output = output_directory.absolute()
        parent = output.parent
        parent_identity = _private_output_parent_identity(output)

        receipts: list[dict[str, str]] = []
        directory_identities: dict[str, tuple[int, int]] = {}
        source_commit: str | None = None
        signal_state = {"commit_boundary": False}

        def interrupted(signum: int, frame: object) -> None:
            if signal_state["commit_boundary"]:
                return
            _reject()

        try:
            with _temporary_signal_handlers(interrupted):
                with tempfile.TemporaryDirectory(
                    prefix=f".{output.name}-", dir=parent
                ) as temporary:
                    workspace = Path(temporary)
                    os.chmod(workspace, 0o700)
                    workspace_identity = _private_workspace_identity(workspace)
                    for phase in PHASES:
                        if _private_workspace_identity(workspace) != workspace_identity:
                            _reject()
                        _verify_intermediate_workspace_entries(
                            workspace,
                            workspace_identity,
                            directory_identities,
                        )
                        try:
                            raw = self._gates[phase].execute(workspace)
                        except ControlledPreflightRejected:
                            raise
                        except Exception:
                            _reject()
                        if _private_workspace_identity(workspace) != workspace_identity:
                            _reject()
                        created_name = PHASE_OUTPUT_DIRECTORIES.get(phase)
                        if created_name is not None:
                            if created_name in directory_identities:
                                _reject()
                            directory_identities[created_name] = (
                                _private_workspace_child_identity(
                                    workspace, workspace_identity, created_name
                                )
                            )
                        _verify_intermediate_workspace_entries(
                            workspace,
                            workspace_identity,
                            directory_identities,
                        )
                        if not isinstance(raw, bytes):
                            _reject()
                        receipt = GateReceipt.parse(raw, phase)
                        if source_commit is None:
                            source_commit = receipt.source_commit
                        elif receipt.source_commit != source_commit:
                            _reject()
                        receipts.append(
                            {
                                "phase": receipt.phase,
                                "receipt_sha256": _sha256(raw),
                                "facts_sha256": receipt.facts_sha256,
                            }
                        )

                    if source_commit is None:
                        _reject()
                    if set(directory_identities) != set(
                        PHASE_OUTPUT_DIRECTORIES.values()
                    ):
                        _reject()
                    if _private_workspace_identity(workspace) != workspace_identity:
                        _reject()
                    evidence = {
                        "schema_version": 1,
                        "outcome": "passed",
                        "source_commit": source_commit,
                        "phases": receipts,
                        "publishing_authorized": False,
                        "deployment_authorized": False,
                    }
                    evidence_payload = _canonical(evidence)
                    evidence_path, evidence_identity = (
                        _write_private_workspace_evidence_with_identity(
                            workspace,
                            evidence_payload,
                            expected_workspace_identity=workspace_identity,
                        )
                    )
                    verified_evidence_identity = _verify_private_workspace_evidence(
                        workspace,
                        evidence_payload,
                        expected_identity=evidence_identity,
                        expected_workspace_identity=workspace_identity,
                    )
                    if verified_evidence_identity != evidence_identity:
                        _reject()
                    _verify_private_workspace_inventory(
                        workspace,
                        workspace_identity,
                        expected_directory_identities=directory_identities,
                        expected_evidence_identity=evidence_identity,
                    )
                    signal_state["commit_boundary"] = True
                    try:
                        _publish_private_workspace(
                            workspace,
                            output,
                            parent_identity=parent_identity,
                            workspace_identity=workspace_identity,
                            expected_directory_identities=directory_identities,
                            expected_evidence=evidence_payload,
                            expected_evidence_identity=evidence_identity,
                        )
                    except ControlledPreflightRejected:
                        signal_state["commit_boundary"] = False
                        raise
        except ControlledPreflightRejected:
            raise
        except OSError:
            _reject()
        return output / EVIDENCE_NAME


@contextmanager
def _temporary_signal_handlers(handler) -> Iterator[None]:
    signals = (signal.SIGINT, signal.SIGTERM)
    previous: dict[int, object] = {}
    try:
        for item in signals:
            previous[item] = signal.getsignal(item)
            signal.signal(item, handler)
    except (OSError, ValueError):
        for item, old in previous.items():
            signal.signal(item, old)
        _reject()
    try:
        yield
    finally:
        for item, old in previous.items():
            signal.signal(item, old)
