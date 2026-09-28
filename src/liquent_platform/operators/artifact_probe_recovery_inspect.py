"""Read-only classification of one run-bound staging artifact probe prefix."""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path

from liquent_platform.operators.artifact_capability_inspect import ARTIFACT_ROOT


_TOKEN = re.compile(r"[0-9a-f]{64}\Z")
_PREFIX = ".liquent-staging-probe-"
_TEMPORARY = ".capability.tmp"
_FINAL = "capability.json"
_CONTENT = b'{"liquent_staging_artifact_probe":1}\n'
_DIGEST = hashlib.sha256(_CONTENT).hexdigest()
_ALLOWED = frozenset({_TEMPORARY, _FINAL})


class ArtifactProbeRecoveryInspectUnavailable(Exception):
    code = "artifact_probe_recovery_inspect_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise ArtifactProbeRecoveryInspectUnavailable


def _read_file(parent: int, name: str) -> tuple[os.stat_result, bytes] | None:
    descriptor = None
    try:
        descriptor = os.open(
            name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent,
        )
        metadata = os.fstat(descriptor)
        chunks = []
        while True:
            chunk = os.read(descriptor, 4096)
            if not chunk:
                break
            chunks.append(chunk)
            if sum(map(len, chunks)) > len(_CONTENT):
                break
        return metadata, b"".join(chunks)
    except OSError as error:
        if error.errno in {errno.ELOOP, errno.ENOTDIR}:
            return None
        raise ArtifactProbeRecoveryInspectUnavailable from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _valid_file(value: tuple[os.stat_result, bytes] | None) -> bool:
    if value is None:
        return False
    metadata, content = value
    return (
        stat.S_ISREG(metadata.st_mode)
        and metadata.st_uid == os.geteuid()
        and stat.S_IMODE(metadata.st_mode) == 0o600
        and metadata.st_size == len(_CONTENT)
        and content == _CONTENT
        and hashlib.sha256(content).hexdigest() == _DIGEST
    )


def classify_probe_prefix(
    run_token: str, *, artifact_root: Path = ARTIFACT_ROOT,
) -> str:
    """Return absent, recoverable, or conflict without mutating the volume."""

    root = probe = None
    try:
        if type(run_token) is not str or _TOKEN.fullmatch(run_token) is None:
            raise ArtifactProbeRecoveryInspectUnavailable
        root = os.open(
            artifact_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        root_metadata = os.fstat(root)
        if (
            not stat.S_ISDIR(root_metadata.st_mode)
            or root_metadata.st_uid != os.geteuid()
            or stat.S_IMODE(root_metadata.st_mode) & 0o022
        ):
            return "conflict"
        prefix = _PREFIX + run_token
        try:
            probe = os.open(
                prefix,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=root,
            )
        except FileNotFoundError:
            return "absent"
        except OSError as error:
            if error.errno in {errno.ELOOP, errno.ENOTDIR}:
                return "conflict"
            raise ArtifactProbeRecoveryInspectUnavailable from None
        metadata = os.fstat(probe)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o700
        ):
            return "conflict"
        names = os.listdir(probe)
        if len(names) != len(set(names)) or not set(names) <= _ALLOWED:
            return "conflict"
        if not names:
            return "recoverable"
        observed = {name: _read_file(probe, name) for name in names}
        if any(not _valid_file(value) for value in observed.values()):
            return "conflict"
        if set(names) == {_TEMPORARY, _FINAL}:
            temporary = observed[_TEMPORARY][0]
            final = observed[_FINAL][0]
            if temporary.st_ino != final.st_ino or temporary.st_dev != final.st_dev:
                return "conflict"
            if temporary.st_nlink != 2 or final.st_nlink != 2:
                return "conflict"
        elif set(names) in ({_TEMPORARY}, {_FINAL}):
            if next(iter(observed.values()))[0].st_nlink != 1:
                return "conflict"
        else:
            return "conflict"
        return "recoverable"
    except ArtifactProbeRecoveryInspectUnavailable:
        raise
    except Exception:
        raise ArtifactProbeRecoveryInspectUnavailable from None
    finally:
        for descriptor in (probe, root):
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass


def inspect(run_token: str) -> bytes:
    outcome = classify_probe_prefix(run_token)
    return (json.dumps({
        "schema_version": 1,
        "inspection": "artifact_probe_recovery",
        "outcome": outcome,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog="liquent-artifact-probe-recovery-inspect", add_help=False)
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
