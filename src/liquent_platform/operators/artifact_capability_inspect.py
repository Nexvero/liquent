"""Run-bound in-image filesystem capability inspection for staging artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path


ARTIFACT_ROOT = Path("/var/lib/liquent/artifacts")
_TOKEN = re.compile(r"[0-9a-f]{64}\Z")
_PREFIX = ".liquent-staging-probe-"
_TEMPORARY = ".capability.tmp"
_FINAL = "capability.json"
_CONTENT = b'{"liquent_staging_artifact_probe":1}\n'
_DIGEST = hashlib.sha256(_CONTENT).hexdigest()


class ArtifactCapabilityInspectUnavailable(Exception):
    code = "artifact_capability_inspect_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise ArtifactCapabilityInspectUnavailable


def _write_all(descriptor: int, content: bytes) -> None:
    remaining = memoryview(content)
    while remaining:
        written = os.write(descriptor, remaining)
        if written < 1:
            raise ArtifactCapabilityInspectUnavailable
        remaining = remaining[written:]


def _read_all(descriptor: int) -> bytes:
    chunks = []
    while True:
        chunk = os.read(descriptor, 4096)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _absent(parent: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=parent, follow_symlinks=False)
        return False
    except FileNotFoundError:
        return True


def _remove_owned_probe(root: int, probe: int, prefix: str) -> None:
    os.unlink(_FINAL, dir_fd=probe)
    os.fsync(probe)
    os.rmdir(prefix, dir_fd=root)
    os.fsync(root)
    if not _absent(root, prefix):
        raise ArtifactCapabilityInspectUnavailable


def inspect_artifact_capabilities(
    run_token: str, *, artifact_root: Path = ARTIFACT_ROOT,
) -> bool:
    """Exercise one exclusive prefix and remove it only after known outcomes."""

    root = probe = temporary = final = None
    prefix = ""
    try:
        if type(run_token) is not str or _TOKEN.fullmatch(run_token) is None:
            raise ArtifactCapabilityInspectUnavailable
        prefix = _PREFIX + run_token
        root = os.open(
            artifact_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        root_metadata = os.fstat(root)
        if (
            not stat.S_ISDIR(root_metadata.st_mode)
            or root_metadata.st_uid != os.geteuid()
            or stat.S_IMODE(root_metadata.st_mode) & 0o022
        ):
            return False
        if not _absent(root, prefix):
            raise ArtifactCapabilityInspectUnavailable
        os.mkdir(prefix, 0o700, dir_fd=root)
        probe = os.open(
            prefix, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=root,
        )
        probe_metadata = os.fstat(probe)
        if (
            not stat.S_ISDIR(probe_metadata.st_mode)
            or probe_metadata.st_uid != os.geteuid()
            or stat.S_IMODE(probe_metadata.st_mode) != 0o700
        ):
            raise ArtifactCapabilityInspectUnavailable
        temporary = os.open(
            _TEMPORARY,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=probe,
        )
        _write_all(temporary, _CONTENT)
        os.fsync(temporary)
        os.close(temporary)
        temporary = None
        os.link(_TEMPORARY, _FINAL, src_dir_fd=probe, dst_dir_fd=probe)
        os.fsync(probe)
        os.unlink(_TEMPORARY, dir_fd=probe)
        os.fsync(probe)
        final = os.open(_FINAL, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=probe)
        metadata = os.fstat(final)
        content = _read_all(final)
        valid = (
            stat.S_ISREG(metadata.st_mode)
            and metadata.st_uid == os.geteuid()
            and metadata.st_nlink == 1
            and stat.S_IMODE(metadata.st_mode) == 0o600
            and len(content) == len(_CONTENT)
            and hashlib.sha256(content).hexdigest() == _DIGEST
            and content == _CONTENT
        )
        os.close(final)
        final = None
        try:
            os.link(_FINAL, _FINAL, src_dir_fd=probe, dst_dir_fd=probe)
        except FileExistsError:
            pass
        else:
            valid = False
        _remove_owned_probe(root, probe, prefix)
        return valid
    except ArtifactCapabilityInspectUnavailable:
        raise
    except Exception:
        raise ArtifactCapabilityInspectUnavailable from None
    finally:
        for descriptor in (final, temporary, probe, root):
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass


def inspect(run_token: str) -> bytes:
    result = inspect_artifact_capabilities(run_token)
    return (json.dumps({
        "schema_version": 1,
        "phase": "artifact_capabilities",
        "facts": {"artifact_capabilities_valid": result},
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog="liquent-artifact-capability-inspect", add_help=False)
    parser.add_argument("--run-token", required=True)
    try:
        arguments = parser.parse_args(argv)
        sys.stdout.buffer.write(inspect(arguments.run_token))
        return 0
    except SystemExit:
        return 2
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
