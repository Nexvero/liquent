"""Fail-closed verification of the installable Liquent Python artifact."""

from __future__ import annotations

import argparse
import base64
import configparser
import csv
from datetime import datetime, timezone
from email.parser import BytesParser
from email.policy import compat32
from hashlib import sha256
import io
from pathlib import Path, PurePosixPath
import re
import unicodedata
import zipfile


REQUIRED_FILES = {
    "liquent_platform/persistence/alembic/env.py",
    "liquent_platform/persistence/alembic/script.py.mako",
    "liquent_platform/persistence/alembic/versions/20260726_0001_platform_baseline.py",
}
REQUIRED_ENTRY_POINTS = {
    "liquent-control-plane = liquent_platform.transport.http.main:main",
    "liquent-health-check = liquent_platform.observability.external_health:main",
    "liquent-migrate = liquent_platform.persistence.migrate:main",
}
FORBIDDEN_NAME_PARTS = {
    ".env",
    ".key",
    ".pem",
    "data/raw",
    "data/processed",
    "operations/secrets",
    "reports/",
}
MAX_WHEEL_ARCHIVE_BYTES = 16 * 1024 * 1024
MAX_WHEEL_MEMBER_COUNT = 2048
MAX_WHEEL_MEMBER_NAME_BYTES = 512
MAX_WHEEL_FILE_BYTES = 4 * 1024 * 1024
MAX_WHEEL_TOTAL_FILE_BYTES = 32 * 1024 * 1024
WHEEL_FILENAME_RE = re.compile(
    r"liquent-(?P<version>[A-Za-z0-9][A-Za-z0-9._]*)-py3-none-any\.whl"
)
EXPECTED_REQUIRES_DIST = [
    "alembic<2,>=1.16",
    "fastapi<1,>=0.115",
    "httpx2<3,>=2",
    "prometheus-client<1,>=0.22",
    "psycopg[binary]<4,>=3.2",
    "pydantic-settings<3,>=2.7",
    "PyJWT[crypto]<3,>=2.13",
    "sqlalchemy<2.1,>=2.0",
    "uvicorn<1,>=0.34",
    'build<2,>=1.3; extra == "dev"',
    'pytest>=7.0; extra == "dev"',
    'setuptools<81,>=80; extra == "dev"',
    'wheel<1,>=0.45; extra == "dev"',
    'streamlit>=1.0; extra == "visual"',
]
EXPECTED_ENTRY_POINT_COUNT = 71
EXPECTED_ENTRY_POINT_SEMANTIC_SHA256 = (
    "ac308f068e56879c41b56a0717918f98495727dde534e3dd63b1e4cd09621872"
)
EXPECTED_ENTRY_POINT_FILE_SHA256 = (
    "f2ed86ee956e2816cbdf3d3037dfdc25a7d5762435291e6486e60987f939ad72"
)
EXPECTED_WHEEL_MEMBER_COUNT = 422
EXPECTED_WHEEL_MEMBER_SET_SHA256 = (
    "6bf34bbda6cceac4faad674be46d5a4527cd56859761143d8fde2a03f7df5f1a"
)


def _wheel_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _render_canonical_wheel(
    infos: list[zipfile.ZipInfo], payloads: dict[str, bytes]
) -> bytes:
    rendered = io.BytesIO()
    with zipfile.ZipFile(
        rendered, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for info in infos:
            archive.writestr(info, payloads[info.filename])
    return rendered.getvalue()


def _validate_wheel_members(infos: list[zipfile.ZipInfo]) -> None:
    if len(infos) > MAX_WHEEL_MEMBER_COUNT:
        raise ValueError("wheel verification failed")
    seen: set[str] = set()
    total = 0
    for info in infos:
        name = info.filename
        path = PurePosixPath(name)
        try:
            name_bytes = len(name.encode("utf-8"))
        except UnicodeEncodeError:
            raise ValueError("wheel verification failed") from None
        mode = (info.external_attr >> 16) & 0xFFFF
        expected_mode = 0o100664 if name.endswith(".dist-info/RECORD") else 0o100644
        if (
            not name
            or name in seen
            or name.startswith("/")
            or "\\" in name
            or str(path) != name
            or any(part in {"", ".", ".."} for part in path.parts)
            or name_bytes > MAX_WHEEL_MEMBER_NAME_BYTES
            or unicodedata.normalize("NFC", name) != name
            or any(unicodedata.category(character).startswith("C") for character in name)
            or info.is_dir()
            or info.flag_bits != 0
            or info.compress_type != zipfile.ZIP_DEFLATED
            or mode != expected_mode
            or info.file_size < 0
            or info.file_size > MAX_WHEEL_FILE_BYTES
        ):
            raise ValueError("wheel verification failed")
        seen.add(name)
        total += info.file_size
        if total > MAX_WHEEL_TOTAL_FILE_BYTES:
            raise ValueError("wheel verification failed")


def _validate_wheel_zip_metadata(
    infos: list[zipfile.ZipInfo],
    *,
    archive_comment: bytes,
    expected_timestamp: tuple[int, int, int, int, int, int] | None = None,
) -> None:
    if archive_comment or not infos:
        raise ValueError("wheel ZIP metadata verification failed")
    timestamp = infos[0].date_time
    if (
        timestamp < (1980, 1, 1, 0, 0, 0)
        or timestamp[5] % 2
        or (expected_timestamp is not None and timestamp != expected_timestamp)
    ):
        raise ValueError("wheel ZIP metadata verification failed")
    if any(
        info.date_time != timestamp
        or info.create_system != 3
        or info.create_version != 20
        or info.extract_version != 20
        or info.reserved != 0
        or info.volume != 0
        or info.internal_attr != 0
        or info.extra
        or info.comment
        for info in infos
    ):
        raise ValueError("wheel ZIP metadata verification failed")


def _wheel_timestamp_from_epoch(epoch: int) -> tuple[int, int, int, int, int, int]:
    if isinstance(epoch, bool) or epoch < 315532800 or epoch > 0xFFFFFFFF:
        raise ValueError("wheel timestamp verification failed")
    try:
        value = datetime.fromtimestamp(epoch, timezone.utc)
    except (OSError, OverflowError, ValueError):
        raise ValueError("wheel timestamp verification failed") from None
    return (
        value.year,
        value.month,
        value.day,
        value.hour,
        value.minute,
        value.second // 2 * 2,
    )


def _single_header(message: object, name: str) -> str:
    values = message.get_all(name, [])  # type: ignore[attr-defined]
    if len(values) != 1:
        raise ValueError("wheel identity verification failed")
    return values[0]


def _metadata_message(raw: bytes) -> object:
    if not raw.endswith(b"\n") or b"\r" in raw:
        raise ValueError("wheel metadata verification failed")
    try:
        message = BytesParser(policy=compat32).parsebytes(raw)
    except (UnicodeError, ValueError):
        raise ValueError("wheel metadata verification failed") from None
    if message.defects:
        raise ValueError("wheel metadata verification failed")
    return message


def _verify_wheel_identity(
    path: Path, archive: zipfile.ZipFile, names: set[str]
) -> str:
    match = WHEEL_FILENAME_RE.fullmatch(path.name)
    if match is None:
        raise ValueError("wheel identity verification failed")
    version = match.group("version")
    dist_info = f"liquent-{version}.dist-info"
    roots = {
        name.split("/", 1)[0]
        for name in names
        if ".dist-info/" in name
    }
    required = {
        f"{dist_info}/METADATA",
        f"{dist_info}/WHEEL",
        f"{dist_info}/entry_points.txt",
        f"{dist_info}/RECORD",
    }
    if roots != {dist_info} or not required.issubset(names):
        raise ValueError("wheel identity verification failed")
    metadata = _metadata_message(archive.read(f"{dist_info}/METADATA"))
    wheel = _metadata_message(archive.read(f"{dist_info}/WHEEL"))
    if (
        _single_header(metadata, "Metadata-Version") != "2.4"
        or _single_header(metadata, "Name") != "liquent"
        or _single_header(metadata, "Version") != version
        or _single_header(metadata, "Requires-Python") != ">=3.10"
        or _single_header(metadata, "License-Expression")
        != "LicenseRef-Proprietary"
        or metadata.get_all("Requires-Dist", []) != EXPECTED_REQUIRES_DIST
        or metadata.get_all("Provides-Extra", []) != ["dev", "visual"]
        or metadata.get_all("Requires-External", [])
        or metadata.get_all("Dynamic", [])
        or _single_header(wheel, "Wheel-Version") != "1.0"
        or _single_header(wheel, "Generator") != "setuptools (80.10.2)"
        or _single_header(wheel, "Root-Is-Purelib") != "true"
        or wheel.get_all("Tag", []) != ["py3-none-any"]
        or list(wheel.keys())
        != ["Wheel-Version", "Generator", "Root-Is-Purelib", "Tag"]
    ):
        raise ValueError("wheel identity verification failed")
    return f"{dist_info}/RECORD"


def _verify_wheel_member_set(
    archive: zipfile.ZipFile,
    names: set[str],
    *,
    dist_info: str,
    expected_count: int | None = None,
    expected_sha256: str | None = None,
) -> None:
    roots = {name.split("/", 1)[0] for name in names}
    top_level = f"{dist_info}/top_level.txt"
    if (
        roots != {"liquent", "liquent_platform", dist_info}
        or top_level not in names
        or archive.read(top_level) != b"liquent\nliquent_platform\n"
        or (expected_count is None) != (expected_sha256 is None)
    ):
        raise ValueError("wheel member-set verification failed")
    if expected_count is not None and expected_sha256 is not None:
        canonical = "".join(f"{name}\n" for name in sorted(names)).encode()
        if len(names) != expected_count or sha256(canonical).hexdigest() != expected_sha256:
            raise ValueError("wheel member-set verification failed")


def _verify_wheel_source_payloads(
    archive: zipfile.ZipFile, names: set[str], source_root: Path
) -> None:
    source_directory = source_root / "src"
    package_roots = (source_directory / "liquent", source_directory / "liquent_platform")
    if source_root.is_symlink() or not source_directory.is_dir():
        raise ValueError("wheel source-payload verification failed")
    source_names: set[str] = set()
    for package_root in package_roots:
        if package_root.is_symlink() or not package_root.is_dir():
            raise ValueError("wheel source-payload verification failed")
        for candidate in package_root.rglob("*"):
            if candidate.is_symlink():
                raise ValueError("wheel source-payload verification failed")
            if candidate.is_file() and candidate.suffix in {".py", ".mako"}:
                source_names.add(candidate.relative_to(source_directory).as_posix())
    wheel_names = {
        name
        for name in names
        if name.startswith("liquent/") or name.startswith("liquent_platform/")
    }
    if source_names != wheel_names:
        raise ValueError("wheel source-payload verification failed")
    for name in sorted(wheel_names):
        candidate = source_directory / PurePosixPath(name)
        if not candidate.is_file() or archive.read(name) != candidate.read_bytes():
            raise ValueError("wheel source-payload verification failed")


def _verify_wheel_record(
    archive: zipfile.ZipFile, infos: list[zipfile.ZipInfo], record_name: str
) -> None:
    try:
        raw = archive.read(record_name)
        if not raw.endswith(b"\n") or b"\r" in raw:
            raise ValueError("wheel RECORD verification failed")
        rows = list(csv.reader(raw.decode("utf-8").splitlines(), strict=True))
    except (csv.Error, UnicodeDecodeError):
        raise ValueError("wheel RECORD verification failed") from None
    if len(rows) != len(infos) or any(len(row) != 3 for row in rows):
        raise ValueError("wheel RECORD verification failed")
    if [row[0] for row in rows] != [info.filename for info in infos]:
        raise ValueError("wheel RECORD verification failed")
    for info, row in zip(infos, rows, strict=True):
        name, digest, size = row
        if name == record_name:
            if digest or size:
                raise ValueError("wheel RECORD verification failed")
            continue
        payload = archive.read(info)
        expected_digest = "sha256=" + base64.urlsafe_b64encode(
            sha256(payload).digest()
        ).rstrip(b"=").decode("ascii")
        if digest != expected_digest or size != str(len(payload)):
            raise ValueError("wheel RECORD verification failed")


def _verify_entry_points(raw: bytes) -> None:
    if not raw.endswith(b"\n") or b"\r" in raw:
        raise ValueError("wheel entry-point verification failed")
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.optionxform = str
    try:
        parser.read_string(raw.decode("utf-8"))
    except (configparser.Error, UnicodeDecodeError):
        raise ValueError("wheel entry-point verification failed") from None
    if parser.sections() != ["console_scripts"]:
        raise ValueError("wheel entry-point verification failed")
    entries = sorted(parser.items("console_scripts"))
    if (
        len(entries) != EXPECTED_ENTRY_POINT_COUNT
        or any(
            re.fullmatch(r"liquent-[a-z0-9-]+", name) is None
            or re.fullmatch(
                r"liquent_platform(?:\.[a-z_][a-z0-9_]*)+:[a-z_][a-z0-9_]*",
                target,
            )
            is None
            for name, target in entries
        )
    ):
        raise ValueError("wheel entry-point verification failed")
    semantic = "".join(f"{name}={target}\n" for name, target in entries).encode()
    rendered = (
        "[console_scripts]\n"
        + "".join(f"{name} = {target}\n" for name, target in entries)
    ).encode()
    if (
        sha256(semantic).hexdigest() != EXPECTED_ENTRY_POINT_SEMANTIC_SHA256
        or raw != rendered
        or sha256(raw).hexdigest() != EXPECTED_ENTRY_POINT_FILE_SHA256
    ):
        raise ValueError("wheel entry-point verification failed")


def verify_wheel(
    path: Path,
    *,
    source_date_epoch: int | None = None,
    expected_member_count: int | None = None,
    expected_member_set_sha256: str | None = None,
    source_root: Path | None = None,
) -> str:
    if (
        path.is_symlink()
        or not path.is_file()
        or path.suffix != ".whl"
        or path.stat().st_size > MAX_WHEEL_ARCHIVE_BYTES
    ):
        raise ValueError("expected exactly one wheel file")
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        _validate_wheel_members(infos)
        expected_timestamp = (
            None
            if source_date_epoch is None
            else _wheel_timestamp_from_epoch(source_date_epoch)
        )
        _validate_wheel_zip_metadata(
            infos,
            archive_comment=archive.comment,
            expected_timestamp=expected_timestamp,
        )
        payloads = {info.filename: archive.read(info) for info in infos}
        for info in infos:
            if len(payloads[info.filename]) != info.file_size:
                raise ValueError("wheel verification failed")
        names = {info.filename for info in infos}
        record_name = _verify_wheel_identity(path, archive, names)
        dist_info = record_name.removesuffix("/RECORD")
        _verify_wheel_member_set(
            archive,
            names,
            dist_info=dist_info,
            expected_count=expected_member_count,
            expected_sha256=expected_member_set_sha256,
        )
        if source_root is not None:
            _verify_wheel_source_payloads(archive, names, source_root)
        _verify_wheel_record(archive, infos, record_name)
        missing = REQUIRED_FILES.difference(names)
        if missing:
            raise ValueError(f"wheel is missing required files: {sorted(missing)}")
        forbidden = sorted(
            name
            for name in names
            if any(part.lower() in name.lower() for part in FORBIDDEN_NAME_PARTS)
        )
        if forbidden:
            raise ValueError(f"wheel contains forbidden paths: {forbidden}")
        entry_point_files = [name for name in names if name.endswith(".dist-info/entry_points.txt")]
        if len(entry_point_files) != 1:
            raise ValueError("wheel must contain exactly one entry_points.txt")
        entry_points = archive.read(entry_point_files[0]).decode("utf-8")
        _verify_entry_points(archive.read(entry_point_files[0]))
        for entry_point in REQUIRED_ENTRY_POINTS:
            if not re.search(rf"^{re.escape(entry_point)}$", entry_points, re.MULTILINE):
                raise ValueError(f"wheel is missing entry point: {entry_point}")
    if _render_canonical_wheel(infos, payloads) != path.read_bytes():
        raise ValueError("wheel compressed-byte verification failed")
    return _wheel_sha256(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    digest = verify_wheel(args.wheel)
    print(f"wheel={args.wheel.name}")
    print(f"sha256={digest}")


if __name__ == "__main__":
    main()
