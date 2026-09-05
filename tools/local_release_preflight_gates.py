#!/usr/bin/env python3
"""Self-measuring local adapters for the controlled release preflight."""

from __future__ import annotations

from dataclasses import dataclass
import copy
from decimal import Decimal, InvalidOperation
import gzip
import hashlib
import io
from importlib import metadata
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
from typing import Callable, Mapping, NoReturn, Sequence
import unicodedata
import zipfile
import zlib

from tools.controlled_release_preflight import PHASES
from tools.operational_release_bundle import (
    EXPECTED_ENTRY_POINT_COUNT,
    EXPECTED_MIGRATION_COUNT,
    EXPECTED_OPERATOR_FILE_COUNT,
    _wheel_details,
    build_bundle,
    verify_bundle,
)
from tools.verify_release_wheel import (
    EXPECTED_WHEEL_MEMBER_COUNT,
    EXPECTED_WHEEL_MEMBER_SET_SHA256,
    WHEEL_FILENAME_RE,
    verify_wheel,
)


LOCKED_TOOLS = {
    "build": "1.5.0",
    "pytest": "9.1.1",
    "setuptools": "80.10.2",
    "wheel": "0.47.0",
}
EXPECTED_PYTHON_VERSION = (3, 12, 14)
EXPECTED_ZLIB_BUILD_VERSION = "1.2.12"
EXPECTED_ZLIB_RUNTIME_VERSION = "1.2.12"
MAX_RELEASE_CANDIDATE_DESCRIPTOR_BYTES = 4096
MAX_VERIFICATION_EVIDENCE_BYTES = 16 * 1024
MAX_LOCAL_RELEASE_BUNDLE_BYTES = 64 * 1024 * 1024
MAX_INSTALLED_TREE_FILES = 4096
MAX_INSTALLED_TREE_DIRECTORIES = 1024
MAX_INSTALLED_TREE_DEPTH = 32
MAX_INSTALLED_TREE_FILE_BYTES = 8 * 1024 * 1024
MAX_INSTALLED_TREE_TOTAL_BYTES = 64 * 1024 * 1024
PRIVATE_WORKSPACE_DIRECTORIES = frozenset(
    {"artifacts", "bundle", "installed-wheel", "sdist-wheel-roundtrip"}
)
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
SUMMARY_RE = re.compile(r"(?P<count>[1-9][0-9]*) passed")
WARNING_RE = re.compile(r"(?P<count>[0-9]+) warnings?")
POSTGRES_VERSION_RE = re.compile(r"[1-9][0-9]*(?:\.[0-9]+){0,2}")
PROCESS_TIMEOUT_SECONDS = 900.0
MAX_PROCESS_OUTPUT_BYTES = 1_048_576
MAX_SDIST_COMPRESSED_BYTES = 16 * 1024 * 1024
MAX_SDIST_UNCOMPRESSED_BYTES = 40 * 1024 * 1024
MAX_SDIST_MEMBER_COUNT = 4096
MAX_SDIST_MEMBER_NAME_BYTES = 1024
MAX_SDIST_FILE_BYTES = 4 * 1024 * 1024
MAX_SDIST_TOTAL_FILE_BYTES = 32 * 1024 * 1024
MAX_SDIST_SOURCE_MTIME = Decimal("253402300799")
MAX_SOURCE_DATE_EPOCH = 0xFFFFFFFF
EXPECTED_SDIST_GZIP_XFL = 2
EXPECTED_SDIST_GZIP_OS = 255
SdistManifest = tuple[tuple[str, bool, int, int, str | None], ...]
GENERATED_SDIST_FILES = {
    "PKG-INFO",
    "setup.cfg",
    "src/liquent.egg-info/PKG-INFO",
    "src/liquent.egg-info/SOURCES.txt",
    "src/liquent.egg-info/dependency_links.txt",
    "src/liquent.egg-info/entry_points.txt",
    "src/liquent.egg-info/requires.txt",
    "src/liquent.egg-info/top_level.txt",
}
EXPECTED_SDIST_SETUP_CFG = b"[egg_info]\ntag_build = \ntag_date = 0\n\n"
EXPECTED_SDIST_REQUIRES = b"""alembic<2,>=1.16
fastapi<1,>=0.115
httpx2<3,>=2
prometheus-client<1,>=0.22
psycopg[binary]<4,>=3.2
pydantic-settings<3,>=2.7
PyJWT[crypto]<3,>=2.13
sqlalchemy<2.1,>=2.0
uvicorn<1,>=0.34

[dev]
build<2,>=1.3
pytest>=7.0
setuptools<81,>=80
wheel<1,>=0.45

[visual]
streamlit>=1.0
"""


class LocalGateRejected(Exception):
    """One detail-limited local gate rejection."""


def _reject() -> NoReturn:
    raise LocalGateRejected("local release preflight gate rejected")


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sdist_root_from_filename(path: Path) -> str:
    name = path.name
    if (
        not name.startswith("liquent-")
        or not name.endswith(".tar.gz")
        or len(name) <= len("liquent-.tar.gz")
    ):
        _reject()
    root = name[: -len(".tar.gz")]
    version = root[len("liquent-") :]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", version):
        _reject()
    return root


def _sdist_manifest(
    entries: Sequence[tuple[tarfile.TarInfo, bytes | None]],
) -> SdistManifest:
    return tuple(
        (
            member.name,
            member.isdir(),
            member.mode,
            member.size,
            None if payload is None else _sha256(payload),
        )
        for member, payload in entries
    )


def _validate_sdist_member_names(
    members: Sequence[tarfile.TarInfo], *, expected_root: str | None = None
) -> None:
    if len(members) > MAX_SDIST_MEMBER_COUNT:
        _reject()
    seen: set[str] = set()
    root: str | None = None
    root_directory_seen = False
    total_file_bytes = 0
    for member in members:
        name = member.name
        path = PurePosixPath(name)
        try:
            name_bytes = len(name.encode("utf-8"))
        except UnicodeEncodeError:
            _reject()
        if (
            not name
            or name_bytes > MAX_SDIST_MEMBER_NAME_BYTES
            or unicodedata.normalize("NFC", name) != name
            or any(unicodedata.category(character).startswith("C") for character in name)
            or name in seen
            or name.startswith("/")
            or "\\" in name
            or str(path) != name
            or any(part in {"", ".", ".."} for part in path.parts)
        ):
            _reject()
        seen.add(name)
        candidate_root = path.parts[0]
        if root is None:
            root = candidate_root
        elif candidate_root != root:
            _reject()
        if expected_root is not None and candidate_root != expected_root:
            _reject()
        if name == candidate_root:
            if not member.isdir() or root_directory_seen:
                _reject()
            root_directory_seen = True
        if set(member.pax_headers) - {"path", "mtime"} or (
            "path" in member.pax_headers and member.pax_headers["path"] != name
        ):
            _reject()
        if "mtime" in member.pax_headers:
            try:
                source_mtime = Decimal(member.pax_headers["mtime"])
            except (InvalidOperation, ValueError):
                _reject()
            if (
                not source_mtime.is_finite()
                or source_mtime < 0
                or source_mtime > MAX_SDIST_SOURCE_MTIME
            ):
                _reject()
        if member.isfile():
            if (
                member.mode != 0o644
                or member.size < 0
                or member.size > MAX_SDIST_FILE_BYTES
            ):
                _reject()
            total_file_bytes += member.size
            if total_file_bytes > MAX_SDIST_TOTAL_FILE_BYTES:
                _reject()
        elif member.mode != 0o755 or member.size != 0:
            _reject()
    if expected_root is not None and not root_directory_seen:
        _reject()


def _normalize_sdist(path: Path, source_date_epoch: str) -> SdistManifest:
    if (
        not source_date_epoch.isdigit()
        or int(source_date_epoch) < 1
        or int(source_date_epoch) > MAX_SOURCE_DATE_EPOCH
    ):
        _reject()
    epoch = int(source_date_epoch)
    expected_root = _sdist_root_from_filename(path)
    temporary_path: Path | None = None
    try:
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size > MAX_SDIST_COMPRESSED_BYTES
        ):
            _reject()
        with tarfile.open(path, "r:gz") as source:
            entries = []
            members = []
            for member in source:
                members.append(member)
                if len(members) > MAX_SDIST_MEMBER_COUNT:
                    _reject()
            _validate_sdist_member_names(members, expected_root=expected_root)
            for member in members:
                if not (member.isdir() or member.isfile()):
                    _reject()
                payload = None
                if member.isfile():
                    extracted = source.extractfile(member)
                    if extracted is None:
                        _reject()
                    payload = extracted.read()
                    if len(payload) != member.size:
                        _reject()
                entries.append((copy.copy(member), payload))
        expected_manifest = _sdist_manifest(
            sorted(entries, key=lambda entry: entry[0].name)
        )
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            tar_bytes = _render_canonical_sdist_tar(entries, epoch=epoch)
            temporary.write(_render_canonical_sdist_gzip(tar_bytes, epoch=epoch))
        _verify_normalized_sdist(
            temporary_path,
            expected_root=expected_root,
            epoch=epoch,
            expected_manifest=expected_manifest,
        )
        os.replace(temporary_path, path)
        temporary_path = None
        return expected_manifest
    except (OSError, tarfile.TarError):
        _reject()
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _verify_normalized_sdist(
    path: Path,
    *,
    expected_root: str,
    epoch: int,
    expected_manifest: SdistManifest,
) -> None:
    try:
        compressed_bytes = path.read_bytes()
        header = compressed_bytes[:10]
        if (
            len(compressed_bytes) < 18
            or len(compressed_bytes) > MAX_SDIST_COMPRESSED_BYTES
            or len(header) != 10
            or header[:3] != b"\x1f\x8b\x08"
            or header[3] != 0
            or int.from_bytes(header[4:8], "little") != epoch
            or header[8] != EXPECTED_SDIST_GZIP_XFL
            or header[9] != EXPECTED_SDIST_GZIP_OS
        ):
            _reject()
        with gzip.GzipFile(fileobj=io.BytesIO(compressed_bytes)) as compressed:
            tar_bytes = compressed.read(MAX_SDIST_UNCOMPRESSED_BYTES + 1)
            if len(tar_bytes) > MAX_SDIST_UNCOMPRESSED_BYTES or compressed.read(1):
                _reject()
        first_member = zlib.decompressobj(wbits=31)
        if (
            first_member.decompress(compressed_bytes) != tar_bytes
            or not first_member.eof
            or first_member.unused_data
        ):
            _reject()
        trailer = compressed_bytes[-8:]
        if (
            int.from_bytes(trailer[:4], "little") != zlib.crc32(tar_bytes) & 0xFFFFFFFF
            or int.from_bytes(trailer[4:], "little") != len(tar_bytes) & 0xFFFFFFFF
        ):
            _reject()
        with tarfile.open(path, "r:gz") as archive:
            entries = []
            members = []
            for member in archive:
                members.append(member)
                if len(members) > MAX_SDIST_MEMBER_COUNT:
                    _reject()
                payload = None
                if member.isfile():
                    extracted = archive.extractfile(member)
                    if extracted is None:
                        _reject()
                    payload = extracted.read()
                entries.append((member, payload))
        _validate_sdist_member_names(members, expected_root=expected_root)
        _validate_sdist_tar_envelope(tar_bytes, members)
        if _render_canonical_sdist_tar(entries, epoch=epoch) != tar_bytes:
            _reject()
        if _render_canonical_sdist_gzip(tar_bytes, epoch=epoch) != compressed_bytes:
            _reject()
        if [member.name for member in members] != sorted(member.name for member in members):
            _reject()
        if any(
            member.mtime != epoch
            or member.uid != 0
            or member.gid != 0
            or member.uname
            or member.gname
            or set(member.pax_headers) - {"path"}
            for member in members
        ):
            _reject()
        if _sdist_manifest(entries) != expected_manifest:
            _reject()
    except (OSError, tarfile.TarError):
        _reject()


def _validate_sdist_tar_envelope(
    tar_bytes: bytes, members: Sequence[tarfile.TarInfo]
) -> None:
    if not members:
        _reject()
    logical_end = max(
        member.offset_data + ((member.size + tarfile.BLOCKSIZE - 1) // tarfile.BLOCKSIZE)
        * tarfile.BLOCKSIZE
        for member in members
    )
    end_markers = 2 * tarfile.BLOCKSIZE
    expected_size = (
        (logical_end + end_markers + tarfile.RECORDSIZE - 1) // tarfile.RECORDSIZE
    ) * tarfile.RECORDSIZE
    if (
        len(tar_bytes) != expected_size
        or len(tar_bytes) % tarfile.RECORDSIZE
        or tar_bytes[logical_end : logical_end + end_markers] != bytes(end_markers)
        or any(tar_bytes[logical_end + end_markers :])
    ):
        _reject()


def _render_canonical_sdist_tar(
    entries: Sequence[tuple[tarfile.TarInfo, bytes | None]], *, epoch: int
) -> bytes:
    rendered = io.BytesIO()
    with tarfile.open(fileobj=rendered, mode="w", format=tarfile.PAX_FORMAT) as target:
        for original, payload in sorted(entries, key=lambda entry: entry[0].name):
            member = copy.copy(original)
            member.uid = 0
            member.gid = 0
            member.uname = ""
            member.gname = ""
            member.mtime = epoch
            member.pax_headers = {}
            target.addfile(
                member,
                None if payload is None else io.BytesIO(payload),
            )
    return rendered.getvalue()


def _render_canonical_sdist_gzip(tar_bytes: bytes, *, epoch: int) -> bytes:
    rendered = io.BytesIO()
    with gzip.GzipFile(
        filename="", mode="wb", fileobj=rendered, mtime=epoch
    ) as compressed:
        compressed.write(tar_bytes)
    return rendered.getvalue()


def _verify_sdist_source_payloads(
    path: Path, source_root: Path, expected_root: str
) -> int:
    source_names = {"README.md", "pyproject.toml"}
    for root, is_candidate in (
        (
            source_root / "src/liquent",
            lambda candidate: candidate.suffix in {".py", ".mako"},
        ),
        (
            source_root / "src/liquent_platform",
            lambda candidate: candidate.suffix in {".py", ".mako"},
        ),
        (
            source_root / "tests",
            lambda candidate: candidate.suffix == ".py"
            and candidate.name.startswith("test_"),
        ),
    ):
        if root.is_symlink() or not root.is_dir():
            _reject()
        for candidate in root.rglob("*"):
            if candidate.is_symlink():
                _reject()
            if candidate.is_file() and is_candidate(candidate):
                source_names.add(candidate.relative_to(source_root).as_posix())
    try:
        with tarfile.open(path, "r:gz") as archive:
            payloads = {}
            for member in archive:
                if not member.isfile():
                    continue
                prefix = f"{expected_root}/"
                if not member.name.startswith(prefix):
                    _reject()
                relative = member.name.removeprefix(prefix)
                extracted = archive.extractfile(member)
                if extracted is None:
                    _reject()
                payloads[relative] = extracted.read()
    except (OSError, tarfile.TarError):
        _reject()
    if not GENERATED_SDIST_FILES.issubset(payloads):
        _reject()
    archive_source_names = set(payloads) - GENERATED_SDIST_FILES
    if archive_source_names != source_names:
        _reject()
    for name in sorted(source_names):
        candidate = source_root / PurePosixPath(name)
        if (
            candidate.is_symlink()
            or not candidate.is_file()
            or payloads[name] != candidate.read_bytes()
        ):
            _reject()
    return len(source_names)


def _validate_sdist_generated_payloads(
    payloads: Mapping[str, bytes],
    wheel_payloads: Mapping[str, bytes],
    archive_names: set[str],
) -> str:
    sources_raw = payloads.get("src/liquent.egg-info/SOURCES.txt", b"")
    try:
        sources = sources_raw.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        _reject()
    expected_sources = archive_names - {"PKG-INFO", "setup.cfg"}
    if (
        sources_raw.endswith(b"\n")
        or not sources_raw
        or b"\r" in sources_raw
        or len(sources) != len(set(sources))
        or set(sources) != expected_sources
        or payloads.get("PKG-INFO") != payloads.get("src/liquent.egg-info/PKG-INFO")
        or payloads.get("PKG-INFO") != wheel_payloads.get("METADATA")
        or payloads.get("src/liquent.egg-info/entry_points.txt")
        != wheel_payloads.get("entry_points.txt")
        or payloads.get("src/liquent.egg-info/top_level.txt")
        != wheel_payloads.get("top_level.txt")
        or payloads.get("src/liquent.egg-info/dependency_links.txt") != b"\n"
        or payloads.get("src/liquent.egg-info/requires.txt")
        != EXPECTED_SDIST_REQUIRES
        or payloads.get("setup.cfg") != EXPECTED_SDIST_SETUP_CFG
    ):
        _reject()
    canonical = b"".join(
        name.encode("utf-8") + b"\0" + payloads[name]
        for name in sorted(GENERATED_SDIST_FILES)
    )
    return _sha256(canonical)


def _verify_sdist_generated_metadata(
    sdist: Path, wheel: Path, expected_root: str
) -> str:
    try:
        with tarfile.open(sdist, "r:gz") as archive:
            payloads = {}
            archive_names = set()
            for member in archive:
                if not member.isfile():
                    continue
                relative = member.name.removeprefix(f"{expected_root}/")
                archive_names.add(relative)
                if relative in GENERATED_SDIST_FILES:
                    extracted = archive.extractfile(member)
                    if extracted is None:
                        _reject()
                    payloads[relative] = extracted.read()
        with zipfile.ZipFile(wheel) as archive:
            wheel_payloads = {
                name.rsplit("/", 1)[1]: archive.read(name)
                for name in archive.namelist()
                if name.endswith(("/METADATA", "/entry_points.txt", "/top_level.txt"))
            }
    except (OSError, tarfile.TarError, zipfile.BadZipFile):
        _reject()
    return _validate_sdist_generated_payloads(
        payloads, wheel_payloads, archive_names
    )


@dataclass(frozen=True)
class CommandResult:
    stdout: bytes
    stderr: bytes


CommandRunner = Callable[[Sequence[str], Path, Mapping[str, str]], CommandResult]


def subprocess_runner(
    argv: Sequence[str], cwd: Path, environment: Mapping[str, str]
) -> CommandResult:
    return _bounded_subprocess(
        argv,
        cwd,
        environment,
        timeout_seconds=PROCESS_TIMEOUT_SECONDS,
        max_output_bytes=MAX_PROCESS_OUTPUT_BYTES,
    )


def _bounded_subprocess(
    argv: Sequence[str],
    cwd: Path,
    environment: Mapping[str, str],
    *,
    timeout_seconds: float,
    max_output_bytes: int,
) -> CommandResult:
    if (
        not argv
        or isinstance(timeout_seconds, bool)
        or timeout_seconds <= 0
        or isinstance(max_output_bytes, bool)
        or max_output_bytes < 1
    ):
        _reject()
    try:
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            process = subprocess.Popen(
                list(argv),
                cwd=cwd,
                env=dict(environment),
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
            try:
                return_code = process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                _terminate_process_group(process)
                _reject()
            except BaseException:
                _terminate_process_group(process)
                raise
            if return_code != 0:
                _reject()
            stdout.seek(0, os.SEEK_END)
            stderr.seek(0, os.SEEK_END)
            stdout_size = stdout.tell()
            stderr_size = stderr.tell()
            if (
                stdout_size > max_output_bytes
                or stderr_size > max_output_bytes
                or stdout_size + stderr_size > max_output_bytes
            ):
                _reject()
            stdout.seek(0)
            stderr.seek(0)
            return CommandResult(stdout.read(), stderr.read())
    except LocalGateRejected:
        raise
    except OSError:
        _reject()


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except OSError:
        try:
            process.kill()
        except OSError:
            pass
    try:
        process.wait(timeout=5.0)
    except (OSError, subprocess.TimeoutExpired):
        pass


class LocalGateContext:
    """Shared private state populated only by successful measured phases."""

    def __init__(
        self,
        source_root: Path,
        *,
        python_executable: str = sys.executable,
        environment: Mapping[str, str] | None = None,
        command_runner: CommandRunner = subprocess_runner,
    ) -> None:
        self.source_root = source_root.absolute()
        self.python_executable = python_executable
        self.environment = dict(os.environ if environment is None else environment)
        self.command_runner = command_runner
        self.test_counts: dict[str, int] = {}
        self.warning_count = 0
        self.postgres_warning_count = 0
        self.postgres_version: str | None = None
        self.bound_source_commit: str | None = None
        self.bound_source_date_epoch: int | None = None
        self.build_runtime_sha256: str | None = None
        self.quality_evidence_sha256: str | None = None
        self.verification_sha256: str | None = None
        self.release_candidate_sha256: str | None = None
        self.release_candidate: Path | None = None
        self.local_bundle_sha256: str | None = None
        self.candidate_output_sha256: str | None = None
        self.final_diff_verified = False
        self.wheel: Path | None = None
        self.sdist: Path | None = None
        self.wheel_sha256: str | None = None
        self.sdist_sha256: str | None = None
        self.distribution_directory_identity: tuple[int, int] | None = None
        self.roundtrip_wheel: Path | None = None
        self.roundtrip_wheel_sha256: str | None = None
        self.roundtrip_directory_identity: tuple[int, int] | None = None
        self.installed_tree_sha256: str | None = None
        self.installed_tree_file_count: int | None = None
        self.installed_tree_total_bytes: int | None = None
        self.installed_tree_identity: tuple[int, int] | None = None
        self.installed_distribution_sha256: str | None = None
        self.distribution_version: str | None = None
        self.distribution_pair_sha256: str | None = None
        self.sdist_manifest: SdistManifest | None = None
        self.sdist_root: str | None = None
        self.sdist_source_file_count: int | None = None
        self.sdist_generated_metadata_sha256: str | None = None
        self.verification: Path | None = None
        self.bundle: Path | None = None

    def command(self, argv: Sequence[str]) -> CommandResult:
        return self.command_runner(argv, self.source_root, self.environment)

    def source_commit(self) -> str:
        head = self.command(("git", "rev-parse", "HEAD")).stdout.decode("ascii").strip()
        status = self.command(
            ("git", "status", "--porcelain=v1", "--untracked-files=all")
        ).stdout
        if not COMMIT_RE.fullmatch(head) or status:
            _reject()
        return head


def _distribution_pair_identity(
    wheel: Path,
    sdist: Path,
    *,
    source_commit: str,
    source_date_epoch: int,
    build_runtime_sha256: str,
    quality_evidence_sha256: str,
) -> dict[str, object]:
    wheel_match = WHEEL_FILENAME_RE.fullmatch(wheel.name)
    sdist_root = _sdist_root_from_filename(sdist)
    if (
        wheel_match is None
        or sdist_root != f"liquent-{wheel_match.group('version')}"
        or not COMMIT_RE.fullmatch(source_commit)
        or isinstance(source_date_epoch, bool)
        or source_date_epoch < 1
        or source_date_epoch > MAX_SOURCE_DATE_EPOCH
        or re.fullmatch(r"[0-9a-f]{64}", build_runtime_sha256) is None
        or re.fullmatch(r"[0-9a-f]{64}", quality_evidence_sha256) is None
    ):
        _reject()
    facts = {
        "build_runtime_sha256": build_runtime_sha256,
        "quality_evidence_sha256": quality_evidence_sha256,
        "sdist_name": sdist.name,
        "sdist_sha256": _sha256(sdist.read_bytes()),
        "source_commit": source_commit,
        "source_date_epoch": source_date_epoch,
        "version": wheel_match.group("version"),
        "wheel_name": wheel.name,
        "wheel_sha256": _sha256(wheel.read_bytes()),
    }
    return {**facts, "pair_sha256": _sha256(_canonical(facts))}


def _verify_distribution_pair(context: LocalGateContext) -> tuple[Path, Path]:
    wheel = context.wheel
    sdist = context.sdist
    if (
        wheel is None
        or sdist is None
        or context.wheel_sha256 is None
        or context.sdist_sha256 is None
        or context.distribution_version is None
        or context.distribution_pair_sha256 is None
        or context.bound_source_commit is None
        or context.bound_source_date_epoch is None
        or context.build_runtime_sha256 is None
        or context.quality_evidence_sha256 is None
        or context.distribution_directory_identity is None
        or wheel.parent != sdist.parent
    ):
        _reject()
    if (
        _private_output_directory_identity(wheel.parent)
        != context.distribution_directory_identity
    ):
        _reject()
    if _sha256(_canonical(_quality_evidence_facts(context))) != context.quality_evidence_sha256:
        _reject()
    identity = _distribution_pair_identity(
        wheel,
        sdist,
        source_commit=context.bound_source_commit,
        source_date_epoch=context.bound_source_date_epoch,
        build_runtime_sha256=context.build_runtime_sha256,
        quality_evidence_sha256=context.quality_evidence_sha256,
    )
    if (
        identity["wheel_sha256"] != context.wheel_sha256
        or identity["sdist_sha256"] != context.sdist_sha256
        or identity["version"] != context.distribution_version
        or identity["pair_sha256"] != context.distribution_pair_sha256
    ):
        _reject()
    return wheel, sdist


class MeasuredGate:
    phase: str

    def __init__(self, context: LocalGateContext) -> None:
        if self.phase not in PHASES:
            _reject()
        self.context = context

    def measure(self, workspace: Path) -> Mapping[str, object]:
        raise NotImplementedError

    def execute(self, workspace: Path) -> bytes:
        commit = self.context.source_commit()
        if self.context.bound_source_commit is None:
            self.context.bound_source_commit = commit
        elif self.context.bound_source_commit != commit:
            _reject()
        if self.context.bound_source_date_epoch is not None and (
            self.context.environment.get("SOURCE_DATE_EPOCH")
            != str(self.context.bound_source_date_epoch)
        ):
            _reject()
        try:
            facts = dict(self.measure(workspace))
        except LocalGateRejected:
            raise
        except Exception:
            _reject()
        if not facts or any(not isinstance(key, str) or not key for key in facts):
            _reject()
        digest = _sha256(_canonical(facts))
        return _canonical(
            {
                "facts_sha256": digest,
                "phase": self.phase,
                "schema_version": 1,
                "source_commit": commit,
                "status": "passed",
            }
        )


def _compression_runtime_facts() -> dict[str, str]:
    if (
        sys.version_info[:3] != EXPECTED_PYTHON_VERSION
        or zlib.ZLIB_VERSION != EXPECTED_ZLIB_BUILD_VERSION
        or zlib.ZLIB_RUNTIME_VERSION != EXPECTED_ZLIB_RUNTIME_VERSION
    ):
        _reject()
    return {
        "python": ".".join(str(part) for part in EXPECTED_PYTHON_VERSION),
        "zlib_build": EXPECTED_ZLIB_BUILD_VERSION,
        "zlib_runtime": EXPECTED_ZLIB_RUNTIME_VERSION,
    }


class RuntimeGate(MeasuredGate):
    phase = "runtime"

    def measure(self, workspace: Path) -> Mapping[str, object]:
        facts = _compression_runtime_facts()
        versions: dict[str, str] = {}
        try:
            for package, expected in LOCKED_TOOLS.items():
                actual = metadata.version(package)
                if actual != expected:
                    _reject()
                versions[package] = actual
        except metadata.PackageNotFoundError:
            _reject()
        measured = {**facts, "tools": versions}
        self.context.build_runtime_sha256 = _sha256(_canonical(measured))
        return {**measured, "build_runtime_sha256": self.context.build_runtime_sha256}


class SourceGate(MeasuredGate):
    phase = "source"

    def measure(self, workspace: Path) -> Mapping[str, object]:
        commit = self.context.bound_source_commit
        if commit is None:
            _reject()
        epoch = self.context.command(("git", "show", "-s", "--format=%ct", commit))
        value = epoch.stdout.decode("ascii").strip()
        if not value.isdigit() or int(value) < 1:
            _reject()
        self.context.environment["SOURCE_DATE_EPOCH"] = value
        self.context.bound_source_date_epoch = int(value)
        return {"source_date_epoch": int(value), "tree": "clean"}


def _test_summary(result: CommandResult) -> tuple[int, int]:
    rendered = (result.stdout + b"\n" + result.stderr).decode("utf-8", "replace")
    passed = SUMMARY_RE.findall(rendered)
    warnings = WARNING_RE.findall(rendered)
    if len(passed) != 1:
        _reject()
    return int(passed[0]), int(warnings[-1]) if warnings else 0


class NormalTestsGate(MeasuredGate):
    phase = "normal_tests"

    def measure(self, workspace: Path) -> Mapping[str, object]:
        result = self.context.command(
            (self.context.python_executable, "-m", "pytest", "-q")
        )
        passed, warnings = _test_summary(result)
        self.context.test_counts["normal"] = passed
        self.context.warning_count = warnings
        return {"passed": passed, "warnings": warnings}


def _quality_evidence_facts(context: LocalGateContext) -> dict[str, object]:
    if (
        set(context.test_counts) != {"normal", "postgres"}
        or any(
            isinstance(count, bool) or not isinstance(count, int) or count < 1
            for count in context.test_counts.values()
        )
        or isinstance(context.warning_count, bool)
        or context.warning_count < 0
        or isinstance(context.postgres_warning_count, bool)
        or context.postgres_warning_count < 0
        or context.postgres_version is None
        or POSTGRES_VERSION_RE.fullmatch(context.postgres_version) is None
    ):
        _reject()
    return {
        "normal_command": "python -m pytest -q",
        "normal_passed": context.test_counts["normal"],
        "normal_warnings": context.warning_count,
        "postgres_command": "python -m pytest -m postgres_integration -q",
        "postgres_passed": context.test_counts["postgres"],
        "postgres_warnings": context.postgres_warning_count,
        "postgresql": context.postgres_version,
    }


class PostgresTestsGate(MeasuredGate):
    phase = "postgres_tests"

    def measure(self, workspace: Path) -> Mapping[str, object]:
        if not self.context.environment.get("LIQUENT_TEST_DATABASE_URL"):
            _reject()
        environment = self.context.environment
        environment["LIQUENT_REQUIRE_POSTGRES_TESTS"] = "1"
        result = self.context.command(
            (
                self.context.python_executable,
                "-m",
                "pytest",
                "-m",
                "postgres_integration",
                "-q",
            )
        )
        passed, warnings = _test_summary(result)
        version_result = self.context.command(
            (
                self.context.python_executable,
                "-c",
                "from sqlalchemy import create_engine,text;import os;"
                "e=create_engine(os.environ['LIQUENT_TEST_DATABASE_URL']);"
                "c=e.connect();v=c.scalar(text('SHOW server_version'));"
                "print(str(v).split()[0]);"
                "c.close();e.dispose()",
            )
        )
        version = version_result.stdout.decode("ascii").strip()
        if not POSTGRES_VERSION_RE.fullmatch(version) or version_result.stderr:
            _reject()
        self.context.test_counts["postgres"] = passed
        self.context.postgres_warning_count = warnings
        self.context.postgres_version = version
        quality = _quality_evidence_facts(self.context)
        self.context.quality_evidence_sha256 = _sha256(_canonical(quality))
        return {
            "passed": passed,
            "postgresql": version,
            "quality_evidence_sha256": self.context.quality_evidence_sha256,
            "warnings": warnings,
        }


class DistributionsGate(MeasuredGate):
    phase = "distributions"

    def measure(self, workspace: Path) -> Mapping[str, object]:
        artifacts, artifacts_identity = _create_private_workspace_directory(
            workspace, "artifacts"
        )
        self.context.command(
            (
                self.context.python_executable,
                "-m",
                "build",
                "--no-isolation",
                "--outdir",
                str(artifacts),
            )
        )
        if _private_output_directory_identity(artifacts) != artifacts_identity:
            _reject()
        wheels = list(artifacts.glob("liquent-*.whl"))
        sdists = list(artifacts.glob("liquent-*.tar.gz"))
        if len(wheels) != 1 or len(sdists) != 1:
            _reject()
        epoch = self.context.environment.get("SOURCE_DATE_EPOCH", "")
        manifest = _normalize_sdist(sdists[0], epoch)
        try:
            wheels[0].chmod(0o600)
            sdists[0].chmod(0o600)
        except OSError:
            _reject()
        self.context.wheel, self.context.sdist = wheels[0], sdists[0]
        self.context.sdist_manifest = manifest
        self.context.sdist_root = _sdist_root_from_filename(sdists[0])
        self.context.sdist_source_file_count = _verify_sdist_source_payloads(
            sdists[0], self.context.source_root, self.context.sdist_root
        )
        self.context.sdist_generated_metadata_sha256 = (
            _verify_sdist_generated_metadata(
                sdists[0], wheels[0], self.context.sdist_root
            )
        )
        if (
            self.context.bound_source_commit is None
            or self.context.bound_source_date_epoch is None
            or self.context.build_runtime_sha256 is None
            or self.context.quality_evidence_sha256 is None
        ):
            _reject()
        identity = _distribution_pair_identity(
            wheels[0],
            sdists[0],
            source_commit=self.context.bound_source_commit,
            source_date_epoch=self.context.bound_source_date_epoch,
            build_runtime_sha256=self.context.build_runtime_sha256,
            quality_evidence_sha256=self.context.quality_evidence_sha256,
        )
        self.context.wheel_sha256 = identity["wheel_sha256"]
        self.context.sdist_sha256 = identity["sdist_sha256"]
        self.context.distribution_version = identity["version"]
        self.context.distribution_pair_sha256 = identity["pair_sha256"]
        if _private_output_directory_identity(artifacts) != artifacts_identity:
            _reject()
        self.context.distribution_directory_identity = artifacts_identity
        return {
            "pair_sha256": self.context.distribution_pair_sha256,
            "package_version": self.context.distribution_version,
            "wheel_sha256": self.context.wheel_sha256,
            "sdist_sha256": self.context.sdist_sha256,
        }


class WheelGate(MeasuredGate):
    phase = "wheel"

    def measure(self, workspace: Path) -> Mapping[str, object]:
        wheel, _ = _verify_distribution_pair(self.context)
        epoch = self.context.environment.get("SOURCE_DATE_EPOCH", "")
        if (
            not epoch.isdigit()
            or verify_wheel(
                wheel,
                source_date_epoch=int(epoch),
                expected_member_count=EXPECTED_WHEEL_MEMBER_COUNT,
                expected_member_set_sha256=EXPECTED_WHEEL_MEMBER_SET_SHA256,
                source_root=self.context.source_root,
            )
            != _sha256(wheel.read_bytes())
        ):
            _reject()
        details = _wheel_details(wheel.read_bytes())
        if (
            len(details["entry_points"]) != EXPECTED_ENTRY_POINT_COUNT
            or details["operator_module_count"] != EXPECTED_OPERATOR_FILE_COUNT
            or details["migration_count"] != EXPECTED_MIGRATION_COUNT
            or details["migration_head"] != "20260819_0027"
        ):
            _reject()
        return {
            "entry_points": len(details["entry_points"]),
            "operator_files": details["operator_module_count"],
            "migrations": details["migration_count"],
            "migration_head": details["migration_head"],
        }


class EntryPointsGate(MeasuredGate):
    phase = "entrypoints"

    def measure(self, workspace: Path) -> Mapping[str, object]:
        wheel = self.context.wheel
        if wheel is None or self.context.distribution_version is None:
            _reject()
        installed_distribution = _installed_distribution_identity(wheel)
        if installed_distribution["package_version"] != self.context.distribution_version:
            _reject()
        target, target_identity = _create_private_workspace_directory(
            workspace, "installed-wheel"
        )
        self.context.command(
            (
                self.context.python_executable,
                "-m",
                "pip",
                "--isolated",
                "install",
                "--disable-pip-version-check",
                "--no-compile",
                "--no-deps",
                "--no-index",
                "--target",
                str(target),
                str(wheel),
            )
        )
        if _private_output_directory_identity(target) != target_identity:
            _reject()
        expected_entries = installed_distribution["entry_points"]
        expected_json = json.dumps(
            expected_entries, sort_keys=True, separators=(",", ":")
        )
        script = (
            "import importlib.metadata as m,inspect,json,sys;"
            "from pathlib import Path;"
            f"root=Path({str(target)!r}).resolve(strict=True);"
            "sys.path.insert(0,str(root));"
            f"ds=list(m.distributions(path=[{str(target)!r}]));"
            "assert len(ds)==1;"
            "d=ds[0];"
            "all_entries=list(d.entry_points);"
            f"expected=json.loads({expected_json!r});"
            "assert len(all_entries)==len(expected);"
            "assert all(x.group=='console_scripts' for x in all_entries);"
            "actual=sorted([{'name':x.name,'target':x.value} for x in all_entries],"
            "key=lambda x:(x['name'],x['target']));"
            "assert d.metadata['Name']=='liquent';"
            f"assert d.version=={self.context.distribution_version!r};"
            "assert actual==expected;"
            "lookup={(x.name,x.value):x for x in all_entries};"
            "loaded=[lookup[(x['name'],x['target'])].load() for x in expected];"
            "assert all(callable(x) for x in loaded);"
            "origins=[Path(inspect.getmodule(x).__file__).resolve(strict=True) "
            "for x in loaded];"
            "assert all(x.is_relative_to(root) for x in origins)"
        )
        result = self.context.command_runner(
            (self.context.python_executable, "-I", "-c", script),
            self.context.source_root,
            self.context.environment,
        )
        if (
            result.stdout
            or result.stderr
            or _private_output_directory_identity(target) != target_identity
        ):
            _reject()
        installed = _measure_private_installed_tree(
            target, normalize=True, expected_identity=target_identity
        )
        self.context.installed_tree_sha256 = installed["sha256"]
        self.context.installed_tree_file_count = installed["files"]
        self.context.installed_tree_total_bytes = installed["bytes"]
        self.context.installed_tree_identity = target_identity
        self.context.installed_distribution_sha256 = installed_distribution["sha256"]
        return {
            "installed_distribution_sha256": self.context.installed_distribution_sha256,
            "loaded": EXPECTED_ENTRY_POINT_COUNT,
            **installed,
        }


class SdistGate(MeasuredGate):
    phase = "sdist"

    def measure(self, workspace: Path) -> Mapping[str, object]:
        wheel, sdist = _verify_distribution_pair(self.context)
        manifest = self.context.sdist_manifest
        root = self.context.sdist_root
        source_file_count = self.context.sdist_source_file_count
        generated_metadata_sha256 = self.context.sdist_generated_metadata_sha256
        epoch = self.context.environment.get("SOURCE_DATE_EPOCH", "")
        if (
            manifest is None
            or root is None
            or source_file_count is None
            or generated_metadata_sha256 is None
            or not epoch.isdigit()
        ):
            _reject()
        _verify_normalized_sdist(
            sdist,
            expected_root=root,
            epoch=int(epoch),
            expected_manifest=manifest,
        )
        if (
            _verify_sdist_source_payloads(sdist, self.context.source_root, root)
            != source_file_count
        ):
            _reject()
        if (
            _verify_sdist_generated_metadata(sdist, wheel, root)
            != generated_metadata_sha256
        ):
            _reject()
        try:
            with tarfile.open(sdist, "r:gz") as archive:
                members = archive.getmembers()
        except (OSError, tarfile.TarError):
            _reject()
        names = {member.name for member in members if member.isfile()}
        if (
            any(member.issym() or member.islnk() for member in members)
            or not any(name.endswith("/pyproject.toml") for name in names)
            or not any("/src/liquent_platform/" in name for name in names)
        ):
            _reject()
        roundtrip, roundtrip_identity = _create_private_workspace_directory(
            workspace, "sdist-wheel-roundtrip"
        )
        self.context.command(
            (
                self.context.python_executable,
                "-m",
                "build",
                "--wheel",
                "--no-isolation",
                "--outdir",
                str(roundtrip),
                str(sdist),
            )
        )
        if _private_output_directory_identity(roundtrip) != roundtrip_identity:
            _reject()
        rebuilt = list(roundtrip.glob("liquent-*.whl"))
        if len(rebuilt) != 1:
            _reject()
        try:
            rebuilt[0].chmod(0o600)
        except OSError:
            _reject()
        if (
            rebuilt[0].read_bytes() != wheel.read_bytes()
            or verify_wheel(
                rebuilt[0],
                source_date_epoch=int(epoch),
                expected_member_count=EXPECTED_WHEEL_MEMBER_COUNT,
                expected_member_set_sha256=EXPECTED_WHEEL_MEMBER_SET_SHA256,
                source_root=self.context.source_root,
            )
            != _sha256(rebuilt[0].read_bytes())
        ):
            _reject()
        self.context.roundtrip_wheel = rebuilt[0]
        self.context.roundtrip_wheel_sha256 = _sha256(rebuilt[0].read_bytes())
        if _private_output_directory_identity(roundtrip) != roundtrip_identity:
            _reject()
        self.context.roundtrip_directory_identity = roundtrip_identity
        return {
            "files": len(names),
            "roundtrip_wheel_sha256": self.context.roundtrip_wheel_sha256,
            "sha256": _sha256(sdist.read_bytes()),
            "source_files": source_file_count,
            "generated_metadata_sha256": generated_metadata_sha256,
        }


def _verification_evidence_payload(
    context: LocalGateContext, *, commit: str
) -> bytes:
    if (
        commit != context.bound_source_commit
        or not context.final_diff_verified
        or _sha256(_canonical(_quality_evidence_facts(context)))
        != context.quality_evidence_sha256
    ):
        _reject()
    return _canonical(
        {
            "diff_check": "passed",
            "migration_check": "passed",
            "postgres_passed": context.test_counts["postgres"],
            "schema_version": 1,
            "secret_scan": "passed",
            "source_commit": commit,
            "test_command": "python -m pytest -q; python -m pytest -m postgres_integration -q",
            "total_passed": context.test_counts["normal"],
            "versions": {
                "postgresql": context.postgres_version,
                "psycopg": metadata.version("psycopg"),
                "pytest": metadata.version("pytest"),
                "python": "3.12",
                "sqlalchemy": metadata.version("SQLAlchemy"),
            },
            "warnings": context.warning_count,
            "wheel_import_check": "passed",
        }
    )


def _read_bound_candidate_artifact(
    path: Path, *, max_bytes: int, parent_identity: tuple[int, int]
) -> bytes:
    if _private_output_directory_identity(path.parent) != parent_identity:
        _reject()
    directory_descriptor: int | None = None
    descriptor: int | None = None
    try:
        directory_descriptor = os.open(
            path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        parent_metadata = os.fstat(directory_descriptor)
        if (parent_metadata.st_dev, parent_metadata.st_ino) != parent_identity:
            _reject()
        descriptor = os.open(
            path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_descriptor
        )
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_uid != os.getuid()
            or before.st_nlink != 1
            or before.st_size < 1
            or before.st_size > max_bytes
        ):
            _reject()
        payload = b""
        while chunk := os.read(descriptor, min(1024 * 1024, max_bytes + 1)):
            payload += chunk
            if len(payload) > max_bytes:
                _reject()
        after = os.fstat(descriptor)
        if (
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            or len(payload) != before.st_size
        ):
            _reject()
        return payload
    except LocalGateRejected:
        raise
    except OSError:
        _reject()
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory_descriptor is not None:
            os.close(directory_descriptor)


def _release_candidate_identity(
    context: LocalGateContext, *, bundle: Path
) -> dict[str, object]:
    evidence = context.verification
    if (
        evidence is None
        or context.distribution_pair_sha256 is None
        or context.verification_sha256 is None
        or context.bound_source_commit is None
        or context.distribution_version is None
        or evidence.parent != bundle.parent
        or re.fullmatch(r"[0-9a-f]{64}", context.distribution_pair_sha256) is None
        or re.fullmatch(r"[0-9a-f]{64}", context.verification_sha256) is None
    ):
        _reject()
    parent_identity = _private_output_directory_identity(bundle.parent)
    bundle_payload = _read_bound_candidate_artifact(
        bundle,
        max_bytes=MAX_LOCAL_RELEASE_BUNDLE_BYTES,
        parent_identity=parent_identity,
    )
    evidence_payload = _read_bound_candidate_artifact(
        evidence,
        max_bytes=MAX_VERIFICATION_EVIDENCE_BYTES,
        parent_identity=parent_identity,
    )
    if _sha256(evidence_payload) != context.verification_sha256:
        _reject()
    facts = {
        "schema_version": 1,
        "bundle_name": bundle.name,
        "bundle_size": len(bundle_payload),
        "bundle_sha256": _sha256(bundle_payload),
        "distribution_pair_sha256": context.distribution_pair_sha256,
        "package_version": context.distribution_version,
        "source_commit": context.bound_source_commit,
        "verification_name": evidence.name,
        "verification_size": len(evidence_payload),
        "verification_sha256": context.verification_sha256,
    }
    return {**facts, "release_candidate_sha256": _sha256(_canonical(facts))}


def _write_new_atomic(
    path: Path,
    payload: bytes,
    *,
    max_bytes: int = MAX_RELEASE_CANDIDATE_DESCRIPTOR_BYTES,
) -> None:
    temporary_name: str | None = None
    temporary_descriptor: int | None = None
    directory: int | None = None
    linked = False
    try:
        parent_identity = _private_output_directory_identity(path.parent)
        directory = os.open(
            path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        opened = os.fstat(directory)
        if (opened.st_dev, opened.st_ino) != parent_identity:
            _reject()
        if (
            not payload
            or isinstance(max_bytes, bool)
            or max_bytes < 1
            or len(payload) > max_bytes
            or path.name in {"", ".", ".."}
        ):
            _reject()
        try:
            os.stat(path.name, dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            _reject()
        temporary_name = f".candidate-{secrets.token_hex(16)}.tmp"
        temporary_descriptor = os.open(
            temporary_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory,
        )
        os.fchmod(temporary_descriptor, 0o600)
        view = memoryview(payload)
        while view:
            written = os.write(temporary_descriptor, view)
            if written < 1:
                _reject()
            view = view[written:]
        os.fsync(temporary_descriptor)
        temporary_metadata = os.fstat(temporary_descriptor)
        if (
            not stat.S_ISREG(temporary_metadata.st_mode)
            or stat.S_IMODE(temporary_metadata.st_mode) != 0o600
            or temporary_metadata.st_uid != os.getuid()
            or temporary_metadata.st_nlink != 1
            or temporary_metadata.st_size != len(payload)
        ):
            _reject()
        os.close(temporary_descriptor)
        temporary_descriptor = None
        os.link(
            temporary_name,
            path.name,
            src_dir_fd=directory,
            dst_dir_fd=directory,
            follow_symlinks=False,
        )
        linked = True
        os.unlink(temporary_name, dir_fd=directory)
        temporary_name = None
        os.fsync(directory)
        if (
            (os.fstat(directory).st_dev, os.fstat(directory).st_ino)
            != parent_identity
            or _private_output_directory_identity(path.parent) != parent_identity
        ):
            _reject()
    except LocalGateRejected:
        if linked and directory is not None:
            try:
                os.unlink(path.name, dir_fd=directory)
            except OSError:
                pass
        raise
    except OSError:
        if linked and directory is not None:
            try:
                os.unlink(path.name, dir_fd=directory)
            except OSError:
                pass
        _reject()
    finally:
        if temporary_descriptor is not None:
            os.close(temporary_descriptor)
        if temporary_name is not None and directory is not None:
            try:
                os.unlink(temporary_name, dir_fd=directory)
            except OSError:
                pass
        if directory is not None:
            os.close(directory)


def _private_output_directory_identity(path: Path) -> tuple[int, int]:
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        metadata = os.fstat(descriptor)
    except OSError:
        _reject()
    try:
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o700
            or metadata.st_uid != os.getuid()
        ):
            _reject()
        return metadata.st_dev, metadata.st_ino
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _create_private_workspace_directory(
    workspace: Path, name: str
) -> tuple[Path, tuple[int, int]]:
    workspace_descriptor: int | None = None
    created = False
    try:
        if name not in PRIVATE_WORKSPACE_DIRECTORIES:
            _reject()
        workspace_identity = _private_output_directory_identity(workspace)
        workspace_descriptor = os.open(
            workspace, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        opened = os.fstat(workspace_descriptor)
        if (opened.st_dev, opened.st_ino) != workspace_identity:
            _reject()
        os.mkdir(name, mode=0o700, dir_fd=workspace_descriptor)
        created = True
        output = workspace / name
        output_identity = _private_output_directory_identity(output)
        os.fsync(workspace_descriptor)
        if (
            (os.fstat(workspace_descriptor).st_dev, os.fstat(workspace_descriptor).st_ino)
            != workspace_identity
            or _private_output_directory_identity(workspace) != workspace_identity
            or _private_output_directory_identity(output) != output_identity
        ):
            _reject()
        return output, output_identity
    except LocalGateRejected:
        if created and workspace_descriptor is not None:
            try:
                os.rmdir(name, dir_fd=workspace_descriptor)
            except OSError:
                pass
        raise
    except OSError:
        if created and workspace_descriptor is not None:
            try:
                os.rmdir(name, dir_fd=workspace_descriptor)
            except OSError:
                pass
        _reject()
    finally:
        if workspace_descriptor is not None:
            os.close(workspace_descriptor)


def _create_private_candidate_output(workspace: Path) -> tuple[Path, tuple[int, int]]:
    return _create_private_workspace_directory(workspace, "bundle")


def _seal_local_bundle(path: Path, *, parent_identity: tuple[int, int]) -> str:
    if _private_output_directory_identity(path.parent) != parent_identity:
        _reject()
    directory_descriptor: int | None = None
    descriptor: int | None = None
    try:
        directory_descriptor = os.open(
            path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        parent_metadata = os.fstat(directory_descriptor)
        if (parent_metadata.st_dev, parent_metadata.st_ino) != parent_identity:
            _reject()
        descriptor = os.open(
            path.name,
            os.O_RDONLY | os.O_NOFOLLOW,
            dir_fd=directory_descriptor,
        )
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or metadata.st_nlink != 1
            or metadata.st_size < 1
            or metadata.st_size > MAX_LOCAL_RELEASE_BUNDLE_BYTES
        ):
            _reject()
        os.fchmod(descriptor, 0o600)
        os.fsync(descriptor)
        digest = hashlib.sha256()
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        sealed = os.fstat(descriptor)
        if (
            stat.S_IMODE(sealed.st_mode) != 0o600
            or (sealed.st_dev, sealed.st_ino, sealed.st_size, sealed.st_mtime_ns)
            != (metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns)
            or (os.fstat(directory_descriptor).st_dev, os.fstat(directory_descriptor).st_ino)
            != parent_identity
        ):
            _reject()
    except LocalGateRejected:
        raise
    except OSError:
        _reject()
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory_descriptor is not None:
            os.close(directory_descriptor)
    if _private_output_directory_identity(path.parent) != parent_identity:
        _reject()
    return digest.hexdigest()


def _verify_release_candidate_descriptor(
    path: Path, identity: Mapping[str, object]
) -> None:
    facts = {key: value for key, value in identity.items() if key != "release_candidate_sha256"}
    expected = _canonical(facts)
    parent_identity = _private_output_directory_identity(path.parent)
    directory_descriptor: int | None = None
    descriptor: int | None = None
    try:
        directory_descriptor = os.open(
            path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        parent_metadata = os.fstat(directory_descriptor)
        if (parent_metadata.st_dev, parent_metadata.st_ino) != parent_identity:
            _reject()
        descriptor = os.open(
            path.name,
            os.O_RDONLY | os.O_NOFOLLOW,
            dir_fd=directory_descriptor,
        )
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_uid != os.getuid()
            or before.st_nlink != 1
            or before.st_size != len(expected)
            or before.st_size > MAX_RELEASE_CANDIDATE_DESCRIPTOR_BYTES
        ):
            _reject()
        payload = b""
        while chunk := os.read(descriptor, MAX_RELEASE_CANDIDATE_DESCRIPTOR_BYTES + 1):
            payload += chunk
            if len(payload) > MAX_RELEASE_CANDIDATE_DESCRIPTOR_BYTES:
                _reject()
        after = os.fstat(descriptor)
        if (
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            or payload != expected
            or _sha256(payload) != identity.get("release_candidate_sha256")
            or (os.fstat(directory_descriptor).st_dev, os.fstat(directory_descriptor).st_ino)
            != parent_identity
        ):
            _reject()
    except LocalGateRejected:
        raise
    except OSError:
        _reject()
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory_descriptor is not None:
            os.close(directory_descriptor)
    if _private_output_directory_identity(path.parent) != parent_identity:
        _reject()


def _verify_verification_evidence_file(
    path: Path,
    *,
    expected_payload: bytes,
    expected_sha256: str,
    parent_identity: tuple[int, int],
) -> None:
    if _private_output_directory_identity(path.parent) != parent_identity:
        _reject()
    directory_descriptor: int | None = None
    descriptor: int | None = None
    try:
        directory_descriptor = os.open(
            path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        parent_metadata = os.fstat(directory_descriptor)
        if (parent_metadata.st_dev, parent_metadata.st_ino) != parent_identity:
            _reject()
        descriptor = os.open(
            path.name,
            os.O_RDONLY | os.O_NOFOLLOW,
            dir_fd=directory_descriptor,
        )
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_uid != os.getuid()
            or before.st_nlink != 1
            or before.st_size != len(expected_payload)
            or before.st_size > MAX_VERIFICATION_EVIDENCE_BYTES
        ):
            _reject()
        payload = b""
        while chunk := os.read(descriptor, MAX_VERIFICATION_EVIDENCE_BYTES + 1):
            payload += chunk
            if len(payload) > MAX_VERIFICATION_EVIDENCE_BYTES:
                _reject()
        after = os.fstat(descriptor)
        if (
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            or payload != expected_payload
            or _sha256(payload) != expected_sha256
            or (os.fstat(directory_descriptor).st_dev, os.fstat(directory_descriptor).st_ino)
            != parent_identity
        ):
            _reject()
    except LocalGateRejected:
        raise
    except OSError:
        _reject()
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory_descriptor is not None:
            os.close(directory_descriptor)
    if _private_output_directory_identity(path.parent) != parent_identity:
        _reject()


def _verify_candidate_output_inventory(
    directory: Path,
    *,
    expected_digests: Mapping[str, str],
    expected_sizes: Mapping[str, int],
) -> str:
    directory_identity = _private_output_directory_identity(directory)
    if (
        len(expected_digests) != 3
        or set(expected_sizes) != set(expected_digests)
        or any(
            not isinstance(size, int)
            or isinstance(size, bool)
            or size < 1
            or size > MAX_LOCAL_RELEASE_BUNDLE_BYTES
            for size in expected_sizes.values()
        )
        or any(
            not name
            or "/" in name
            or name in {".", ".."}
            or not isinstance(digest, str)
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            for name, digest in expected_digests.items()
        )
    ):
        _reject()
    directory_descriptor: int | None = None
    try:
        directory_descriptor = os.open(
            directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        directory_metadata = os.fstat(directory_descriptor)
        if (
            (directory_metadata.st_dev, directory_metadata.st_ino)
            != directory_identity
            or stat.S_IMODE(directory_metadata.st_mode) != 0o700
            or directory_metadata.st_uid != os.getuid()
            or set(os.listdir(directory_descriptor)) != set(expected_digests)
        ):
            _reject()
        files = []
        for name in sorted(expected_digests):
            descriptor: int | None = None
            try:
                descriptor = os.open(
                    name,
                    os.O_RDONLY | os.O_NOFOLLOW,
                    dir_fd=directory_descriptor,
                )
                before = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(before.st_mode)
                    or stat.S_IMODE(before.st_mode) != 0o600
                    or before.st_uid != os.getuid()
                    or before.st_nlink != 1
                    or before.st_size != expected_sizes[name]
                ):
                    _reject()
                digest = hashlib.sha256()
                size = 0
                while chunk := os.read(descriptor, 1024 * 1024):
                    digest.update(chunk)
                    size += len(chunk)
                after = os.fstat(descriptor)
                if (
                    (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                    != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                    or size != before.st_size
                    or digest.hexdigest() != expected_digests[name]
                ):
                    _reject()
                files.append(
                    {"name": name, "sha256": digest.hexdigest(), "size": size}
                )
            finally:
                if descriptor is not None:
                    os.close(descriptor)
        if (
            set(os.listdir(directory_descriptor)) != set(expected_digests)
            or (os.fstat(directory_descriptor).st_dev, os.fstat(directory_descriptor).st_ino)
            != directory_identity
        ):
            _reject()
        return _sha256(_canonical({"files": files}))
    except LocalGateRejected:
        raise
    except OSError:
        _reject()
    finally:
        if directory_descriptor is not None:
            os.close(directory_descriptor)


def _verify_private_artifact_inventory(
    directory: Path,
    *,
    expected_digests: Mapping[str, str],
    expected_count: int,
    expected_directory_identity: tuple[int, int] | None = None,
) -> str:
    directory_identity = _private_output_directory_identity(directory)
    if (
        (
            expected_directory_identity is not None
            and directory_identity != expected_directory_identity
        )
        or expected_count not in {1, 2}
        or len(expected_digests) != expected_count
        or any(
            not name
            or "/" in name
            or not isinstance(digest, str)
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            for name, digest in expected_digests.items()
        )
    ):
        _reject()
    directory_descriptor: int | None = None
    try:
        directory_descriptor = os.open(
            directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        opened = os.fstat(directory_descriptor)
        if (
            (opened.st_dev, opened.st_ino) != directory_identity
            or set(os.listdir(directory_descriptor)) != set(expected_digests)
        ):
            _reject()
        facts = []
        for name in sorted(expected_digests):
            descriptor: int | None = None
            try:
                descriptor = os.open(
                    name,
                    os.O_RDONLY | os.O_NOFOLLOW,
                    dir_fd=directory_descriptor,
                )
                before = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(before.st_mode)
                    or stat.S_IMODE(before.st_mode) != 0o600
                    or before.st_uid != os.getuid()
                    or before.st_nlink != 1
                    or before.st_size < 1
                    or before.st_size > MAX_LOCAL_RELEASE_BUNDLE_BYTES
                ):
                    _reject()
                digest = hashlib.sha256()
                size = 0
                while chunk := os.read(descriptor, 1024 * 1024):
                    digest.update(chunk)
                    size += len(chunk)
                after = os.fstat(descriptor)
                if (
                    (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                    != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                    or size != before.st_size
                    or digest.hexdigest() != expected_digests[name]
                ):
                    _reject()
                facts.append(
                    {"name": name, "sha256": digest.hexdigest(), "size": size}
                )
            finally:
                if descriptor is not None:
                    os.close(descriptor)
        if (
            set(os.listdir(directory_descriptor)) != set(expected_digests)
            or (os.fstat(directory_descriptor).st_dev, os.fstat(directory_descriptor).st_ino)
            != directory_identity
        ):
            _reject()
        return _sha256(_canonical({"files": facts}))
    except LocalGateRejected:
        raise
    except OSError:
        _reject()
    finally:
        if directory_descriptor is not None:
            os.close(directory_descriptor)


def _verify_distribution_artifact_inventory(
    directory: Path,
    *,
    expected_digests: Mapping[str, str],
    expected_directory_identity: tuple[int, int] | None = None,
) -> str:
    return _verify_private_artifact_inventory(
        directory,
        expected_digests=expected_digests,
        expected_count=2,
        expected_directory_identity=expected_directory_identity,
    )


def _verify_roundtrip_artifact_inventory(
    directory: Path,
    *,
    expected_digests: Mapping[str, str],
    expected_directory_identity: tuple[int, int] | None = None,
) -> str:
    return _verify_private_artifact_inventory(
        directory,
        expected_digests=expected_digests,
        expected_count=1,
        expected_directory_identity=expected_directory_identity,
    )


def _measure_private_installed_tree(
    root: Path,
    *,
    normalize: bool,
    expected_identity: tuple[int, int] | None = None,
) -> dict[str, object]:
    root_identity = _private_output_directory_identity(root)
    if expected_identity is not None and root_identity != expected_identity:
        _reject()
    root_descriptor: int | None = None
    facts: list[dict[str, object]] = []
    file_count = 0
    directory_count = 0
    total_bytes = 0

    def scan(directory: int, prefix: str, depth: int) -> None:
        nonlocal file_count, directory_count, total_bytes
        if depth > MAX_INSTALLED_TREE_DEPTH:
            _reject()
        names = sorted(os.listdir(directory))
        for name in names:
            if not name or "/" in name or len(os.fsencode(name)) > 255:
                _reject()
            relative = f"{prefix}/{name}" if prefix else name
            metadata = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if stat.S_ISDIR(metadata.st_mode):
                directory_count += 1
                if directory_count > MAX_INSTALLED_TREE_DIRECTORIES:
                    _reject()
                child = os.open(
                    name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=directory,
                )
                try:
                    opened = os.fstat(child)
                    if (
                        opened.st_uid != os.getuid()
                        or (opened.st_dev, opened.st_ino)
                        != (metadata.st_dev, metadata.st_ino)
                    ):
                        _reject()
                    if normalize:
                        os.fchmod(child, 0o700)
                    elif stat.S_IMODE(opened.st_mode) != 0o700:
                        _reject()
                    facts.append({"kind": "directory", "path": relative})
                    scan(child, relative, depth + 1)
                    after = os.fstat(child)
                    if (
                        (after.st_dev, after.st_ino)
                        != (opened.st_dev, opened.st_ino)
                        or after.st_uid != os.getuid()
                        or stat.S_IMODE(after.st_mode) != 0o700
                    ):
                        _reject()
                finally:
                    os.close(child)
            elif stat.S_ISREG(metadata.st_mode):
                file_count += 1
                if file_count > MAX_INSTALLED_TREE_FILES:
                    _reject()
                child = os.open(
                    name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory
                )
                try:
                    before = os.fstat(child)
                    if (
                        before.st_uid != os.getuid()
                        or before.st_nlink != 1
                        or before.st_size > MAX_INSTALLED_TREE_FILE_BYTES
                        or (before.st_dev, before.st_ino)
                        != (metadata.st_dev, metadata.st_ino)
                    ):
                        _reject()
                    if normalize:
                        os.fchmod(child, 0o600)
                    elif stat.S_IMODE(before.st_mode) != 0o600:
                        _reject()
                    digest = hashlib.sha256()
                    size = 0
                    while chunk := os.read(child, 1024 * 1024):
                        digest.update(chunk)
                        size += len(chunk)
                    total_bytes += size
                    after = os.fstat(child)
                    if (
                        total_bytes > MAX_INSTALLED_TREE_TOTAL_BYTES
                        or size != before.st_size
                        or after.st_uid != os.getuid()
                        or after.st_nlink != 1
                        or stat.S_IMODE(after.st_mode) != 0o600
                        or (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                        != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                    ):
                        _reject()
                    facts.append(
                        {
                            "kind": "file",
                            "path": relative,
                            "sha256": digest.hexdigest(),
                            "size": size,
                        }
                    )
                finally:
                    os.close(child)
            else:
                _reject()
        if sorted(os.listdir(directory)) != names:
            _reject()

    try:
        root_descriptor = os.open(
            root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        opened = os.fstat(root_descriptor)
        if (opened.st_dev, opened.st_ino) != root_identity:
            _reject()
        scan(root_descriptor, "", 0)
        if file_count < 1 or directory_count < 1:
            _reject()
        if normalize:
            os.fsync(root_descriptor)
        if _private_output_directory_identity(root) != root_identity:
            _reject()
        return {
            "bytes": total_bytes,
            "files": file_count,
            "sha256": _sha256(_canonical({"entries": facts})),
        }
    except LocalGateRejected:
        raise
    except OSError:
        _reject()
    finally:
        if root_descriptor is not None:
            os.close(root_descriptor)


def _installed_distribution_identity(wheel: Path) -> dict[str, object]:
    try:
        details = _wheel_details(wheel.read_bytes())
    except OSError:
        _reject()
    entries = details.get("entry_points")
    package_name = details.get("package_name")
    package_version = details.get("package_version")
    if (
        package_name != "liquent"
        or not isinstance(package_version, str)
        or not isinstance(entries, list)
        or len(entries) != EXPECTED_ENTRY_POINT_COUNT
        or any(
            not isinstance(entry, dict)
            or set(entry) != {"name", "target"}
            or not isinstance(entry["name"], str)
            or not entry["name"]
            or not isinstance(entry["target"], str)
            or not entry["target"]
            for entry in entries
        )
    ):
        _reject()
    normalized = sorted(entries, key=lambda entry: (entry["name"], entry["target"]))
    if len({entry["name"] for entry in normalized}) != len(normalized):
        _reject()
    facts = {
        "entry_points": normalized,
        "package_name": package_name,
        "package_version": package_version,
        "schema_version": 1,
    }
    return {**facts, "sha256": _sha256(_canonical(facts))}


class BundleGate(MeasuredGate):
    phase = "bundle"

    def measure(self, workspace: Path) -> Mapping[str, object]:
        wheel, sdist = _verify_distribution_pair(self.context)
        if self.context.wheel_sha256 is None or self.context.sdist_sha256 is None:
            _reject()
        distribution_artifact_inventory_sha256 = (
            _verify_distribution_artifact_inventory(
                wheel.parent,
                expected_digests={
                    wheel.name: self.context.wheel_sha256,
                    sdist.name: self.context.sdist_sha256,
                },
                expected_directory_identity=self.context.distribution_directory_identity,
            )
        )
        roundtrip_wheel = self.context.roundtrip_wheel
        roundtrip_wheel_sha256 = self.context.roundtrip_wheel_sha256
        if (
            roundtrip_wheel is None
            or roundtrip_wheel_sha256 != self.context.wheel_sha256
            or self.context.roundtrip_directory_identity is None
        ):
            _reject()
        roundtrip_artifact_inventory_sha256 = _verify_roundtrip_artifact_inventory(
            roundtrip_wheel.parent,
            expected_digests={roundtrip_wheel.name: roundtrip_wheel_sha256},
            expected_directory_identity=self.context.roundtrip_directory_identity,
        )
        installed_tree_identity = self.context.installed_tree_identity
        if installed_tree_identity is None:
            _reject()
        installed = _measure_private_installed_tree(
            workspace / "installed-wheel",
            normalize=False,
            expected_identity=installed_tree_identity,
        )
        installed_distribution = _installed_distribution_identity(wheel)
        if (
            installed["sha256"] != self.context.installed_tree_sha256
            or installed["files"] != self.context.installed_tree_file_count
            or installed["bytes"] != self.context.installed_tree_total_bytes
            or installed_distribution["sha256"]
            != self.context.installed_distribution_sha256
        ):
            _reject()
        epoch = self.context.environment.get("SOURCE_DATE_EPOCH")
        if (
            not epoch
            or set(self.context.test_counts) != {"normal", "postgres"}
            or self.context.postgres_version is None
            or not self.context.final_diff_verified
        ):
            _reject()
        commit = self.context.source_commit()
        output, output_identity = _create_private_candidate_output(workspace)
        evidence = output / "verification.json"
        evidence_payload = _verification_evidence_payload(self.context, commit=commit)
        _write_new_atomic(
            evidence,
            evidence_payload,
            max_bytes=MAX_VERIFICATION_EVIDENCE_BYTES,
        )
        self.context.verification_sha256 = _sha256(evidence_payload)
        _verify_verification_evidence_file(
            evidence,
            expected_payload=evidence_payload,
            expected_sha256=self.context.verification_sha256,
            parent_identity=output_identity,
        )
        bundle = build_bundle(
            source_root=self.context.source_root,
            wheel_path=wheel,
            evidence_path=evidence,
            output_directory=output,
            source_commit=commit,
            source_date_epoch=int(epoch),
        )
        self.context.local_bundle_sha256 = _seal_local_bundle(
            bundle, parent_identity=output_identity
        )
        verified = verify_bundle(bundle)
        _verify_verification_evidence_file(
            evidence,
            expected_payload=evidence_payload,
            expected_sha256=self.context.verification_sha256,
            parent_identity=output_identity,
        )
        if (
            _seal_local_bundle(bundle, parent_identity=output_identity)
            != self.context.local_bundle_sha256
            or verified.get("integrity") != "verified"
            or verified.get("promotable") is not False
        ):
            _reject()
        self.context.verification = evidence
        identity = _release_candidate_identity(self.context, bundle=bundle)
        if identity["bundle_sha256"] != self.context.local_bundle_sha256:
            _reject()
        release_candidate_sha256 = identity["release_candidate_sha256"]
        if not isinstance(release_candidate_sha256, str):
            _reject()
        self.context.release_candidate_sha256 = release_candidate_sha256
        candidate = bundle.parent / "release-candidate.json"
        candidate_payload = _canonical(
            {
                key: value
                for key, value in identity.items()
                if key != "release_candidate_sha256"
            }
        )
        _write_new_atomic(candidate, candidate_payload)
        _verify_release_candidate_descriptor(candidate, identity)
        self.context.release_candidate = candidate
        self.context.bundle = bundle
        self.context.candidate_output_sha256 = _verify_candidate_output_inventory(
            output,
            expected_digests={
                bundle.name: self.context.local_bundle_sha256,
                evidence.name: self.context.verification_sha256,
                candidate.name: self.context.release_candidate_sha256,
            },
            expected_sizes={
                bundle.name: bundle.stat().st_size,
                evidence.name: len(evidence_payload),
                candidate.name: len(candidate_payload),
            },
        )
        return {
            "bundle_sha256": identity["bundle_sha256"],
            "candidate_output_sha256": self.context.candidate_output_sha256,
            "distribution_artifact_inventory_sha256": distribution_artifact_inventory_sha256,
            "installed_distribution_sha256": installed_distribution["sha256"],
            "installed_tree_sha256": installed["sha256"],
            "promotable": False,
            "roundtrip_artifact_inventory_sha256": roundtrip_artifact_inventory_sha256,
            "release_candidate_path": candidate.name,
            "release_candidate_sha256": self.context.release_candidate_sha256,
            "verification_sha256": self.context.verification_sha256,
        }


class FinalDiffGate(MeasuredGate):
    phase = "final_diff"

    def measure(self, workspace: Path) -> Mapping[str, object]:
        self.context.command(("git", "diff", "--check"))
        self.context.final_diff_verified = True
        return {"diff_check": "passed", "source_tree": "clean"}


def local_gate_adapters(context: LocalGateContext) -> dict[str, MeasuredGate]:
    gates: tuple[MeasuredGate, ...] = (
        RuntimeGate(context),
        SourceGate(context),
        NormalTestsGate(context),
        PostgresTestsGate(context),
        DistributionsGate(context),
        WheelGate(context),
        EntryPointsGate(context),
        SdistGate(context),
        FinalDiffGate(context),
        BundleGate(context),
    )
    return {gate.phase: gate for gate in gates}
