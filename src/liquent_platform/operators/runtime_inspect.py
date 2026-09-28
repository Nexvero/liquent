"""Detail-free in-image inspection for three controlled staging phases."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import stat
import sys
from pathlib import Path


RUNTIME_PREFIX = Path("/opt/liquent/venv")
WORKER_SCRIPT = RUNTIME_PREFIX / "bin/liquent-research-worker"
CONFIG_PATH = Path("/run/liquent/research-worker.json")
WORKER_ID_PATH = Path("/run/liquent/research-worker-id")
DATA_ROOT = Path("/var/lib/liquent/research-data")
MOUNTINFO = Path("/proc/self/mountinfo")
PHASE_FACT = {
    "entrypoint": "entrypoint_present",
    "input_ownership": "inputs_owner_only",
    "data_read_only": "data_read_only",
}


class RuntimeInspectUnavailable(Exception):
    code = "runtime_inspect_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise RuntimeInspectUnavailable


def _regular_metadata(path: Path):
    descriptor = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise RuntimeInspectUnavailable
        return metadata
    except RuntimeInspectUnavailable:
        raise
    except Exception:
        raise RuntimeInspectUnavailable from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def inspect_entrypoint(
    *, distribution_loader=importlib.metadata.distribution,
    script_path: Path = WORKER_SCRIPT, runtime_prefix: Path = RUNTIME_PREFIX,
) -> bool:
    try:
        distribution = distribution_loader("liquent")
        matches = [
            entry for entry in distribution.entry_points
            if entry.group == "console_scripts" and entry.name == "liquent-research-worker"
        ]
        if len(matches) != 1 or matches[0].value != "liquent_platform.operators.research_worker:main":
            return False
        if not script_path.is_absolute() or runtime_prefix not in script_path.parents:
            raise RuntimeInspectUnavailable
        metadata = _regular_metadata(script_path)
        return (
            metadata.st_nlink == 1
            and stat.S_IMODE(metadata.st_mode) & 0o022 == 0
            and os.access(script_path, os.X_OK)
        )
    except RuntimeInspectUnavailable:
        raise
    except importlib.metadata.PackageNotFoundError:
        return False
    except Exception:
        raise RuntimeInspectUnavailable from None


def inspect_input_ownership(
    *, config_path: Path = CONFIG_PATH, worker_id_path: Path = WORKER_ID_PATH,
) -> bool:
    try:
        for path in (config_path, worker_id_path):
            metadata = _regular_metadata(path)
            if (
                metadata.st_uid != os.geteuid() or metadata.st_nlink != 1
                or stat.S_IMODE(metadata.st_mode) not in {0o400, 0o600}
            ):
                return False
        return True
    except RuntimeInspectUnavailable:
        raise
    except Exception:
        raise RuntimeInspectUnavailable from None


def _mount_path(value: str) -> str:
    result = bytearray()
    index = 0
    raw = value.encode("ascii")
    while index < len(raw):
        if raw[index:index + 1] == b"\\" and index + 3 < len(raw):
            code = raw[index + 1:index + 4]
            if all(character in b"01234567" for character in code):
                result.append(int(code, 8))
                index += 4
                continue
        result.append(raw[index])
        index += 1
    return result.decode("utf-8")


def _read_only_mount(root: Path, mountinfo: bytes) -> bool:
    try:
        matches = []
        for line in mountinfo.decode("utf-8").splitlines():
            fields = line.split()
            if len(fields) < 10 or "-" not in fields:
                raise RuntimeInspectUnavailable
            separator = fields.index("-")
            if separator < 6 or separator + 3 > len(fields):
                raise RuntimeInspectUnavailable
            if _mount_path(fields[4]) == str(root):
                mount_options = set(fields[5].split(","))
                super_options = set(fields[separator + 3].split(",")) if separator + 3 < len(fields) else set()
                matches.append("ro" in mount_options and "rw" not in mount_options and "rw" not in super_options)
        if len(matches) != 1:
            raise RuntimeInspectUnavailable
        return matches[0]
    except RuntimeInspectUnavailable:
        raise
    except Exception:
        raise RuntimeInspectUnavailable from None


def inspect_data_read_only(
    *, root: Path = DATA_ROOT, mountinfo_path: Path = MOUNTINFO,
) -> bool:
    descriptor = None
    try:
        descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        metadata = os.fstat(descriptor)
        if not stat.S_ISDIR(metadata.st_mode):
            raise RuntimeInspectUnavailable
        mountinfo = mountinfo_path.read_bytes()
        if not mountinfo or len(mountinfo) > 1_048_576:
            raise RuntimeInspectUnavailable
        if not _read_only_mount(root, mountinfo) or os.access(root, os.W_OK):
            return False
        names = os.listdir(descriptor)
        if not names:
            raise RuntimeInspectUnavailable
        for name in names:
            child = None
            try:
                child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=descriptor)
                child_metadata = os.fstat(child)
                if stat.S_ISREG(child_metadata.st_mode) and os.access(root / name, os.W_OK):
                    return False
            except OSError:
                raise RuntimeInspectUnavailable from None
            finally:
                if child is not None:
                    os.close(child)
        return True
    except RuntimeInspectUnavailable:
        raise
    except Exception:
        raise RuntimeInspectUnavailable from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def inspect_phase(phase: str) -> bytes:
    try:
        if phase == "entrypoint":
            result = inspect_entrypoint()
        elif phase == "input_ownership":
            result = inspect_input_ownership()
        elif phase == "data_read_only":
            result = inspect_data_read_only()
        else:
            raise RuntimeInspectUnavailable
        return (json.dumps({
            "schema_version": 1, "phase": phase,
            "facts": {PHASE_FACT[phase]: result},
        }, sort_keys=True, separators=(",", ":")) + "\n").encode()
    except RuntimeInspectUnavailable:
        raise
    except Exception:
        raise RuntimeInspectUnavailable from None


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog="liquent-runtime-inspect", add_help=False)
    parser.add_argument("--phase", required=True)
    try:
        arguments = parser.parse_args(argv)
        sys.stdout.buffer.write(inspect_phase(arguments.phase))
        return 0
    except SystemExit:
        return 2
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
