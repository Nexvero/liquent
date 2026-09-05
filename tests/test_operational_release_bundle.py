from __future__ import annotations

import gzip
import io
import json
import subprocess
import tarfile
import zipfile
from pathlib import Path
from typing import Callable

import pytest

from tools.operational_release_bundle import (
    CONTRACTS,
    EXAMPLE,
    RUNBOOKS,
    BundleRejected,
    EXPECTED_ENTRY_POINT_COUNT,
    EXPECTED_OPERATOR_FILE_COUNT,
    build_bundle,
    main,
    verify_bundle,
)


COMMIT = "a" * 40
EPOCH = 1_700_000_000
VERSION = "1.2.3"


def _wheel(path: Path, *, disconnected: bool = False) -> None:
    metadata = (
        "Metadata-Version: 2.1\nName: liquent\nVersion: 1.2.3\n"
        "Requires-Python: >=3.11\n"
    )
    entries = "[console_scripts]\n" + "".join(
        f"liquent-command-{index:02d} = liquent_platform.operators.command_{index}:main\n"
        for index in range(EXPECTED_ENTRY_POINT_COUNT)
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("liquent-1.2.3.dist-info/METADATA", metadata)
        archive.writestr("liquent-1.2.3.dist-info/entry_points.txt", entries)
        for index in range(42):
            revision = f"20260826_{index + 1:04d}"
            parent = None if index == 0 or (disconnected and index == 18) else (
                f"20260826_{index:04d}"
            )
            archive.writestr(
                f"liquent_platform/persistence/alembic/versions/{revision}.py",
                f"revision: str = {revision!r}\ndown_revision = {parent!r}\n",
            )
        archive.writestr("liquent_platform/operators/__init__.py", "")
        for index in range(EXPECTED_OPERATOR_FILE_COUNT - 1):
            archive.writestr(
                f"liquent_platform/operators/command_{index}.py", "def main(): pass\n"
            )


def _evidence(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_commit": COMMIT,
                "test_command": "python -m pytest -q",
                "total_passed": 2887,
                "postgres_passed": 74,
                "warnings": 53,
                "versions": {
                    "python": "3.12.4",
                    "pytest": "8.4.1",
                    "postgresql": "16.10",
                    "sqlalchemy": "2.0.43",
                    "psycopg": "3.2.9",
                },
                "wheel_import_check": "passed",
                "migration_check": "passed",
                "secret_scan": "passed",
                "diff_check": "passed",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _source(tmp_path: Path) -> tuple[Path, Path, Path]:
    source = tmp_path / "source"
    for directory in ("operations/runbooks", "operations/compose", "docs"):
        (source / directory).mkdir(parents=True, exist_ok=True)
    for name in RUNBOOKS:
        (source / "operations/runbooks" / name).write_text(
            f"# {name}\nControlled operator guidance.\n", encoding="utf-8"
        )
    for name in CONTRACTS:
        (source / "docs" / name).write_text(
            f"# {name}\nRelease contract.\n", encoding="utf-8"
        )
    (source / "operations/compose" / EXAMPLE).write_text(
        "DATABASE_URL=postgresql://placeholder\n", encoding="utf-8"
    )
    wheel = source / f"liquent-{VERSION}-py3-none-any.whl"
    evidence = source / "verification.json"
    _wheel(wheel)
    _evidence(evidence)
    return source, wheel, evidence


def _build(tmp_path: Path, output_name: str = "output") -> Path:
    source, wheel, evidence = _source(tmp_path)
    return build_bundle(
        source_root=source,
        wheel_path=wheel,
        evidence_path=evidence,
        output_directory=tmp_path / output_name,
        source_commit=COMMIT,
        source_date_epoch=EPOCH,
        enforce_clean_source=False,
    )


def _rewrite(
    archive_path: Path,
    mutate: Callable[[list[tuple[tarfile.TarInfo, bytes | None]]], None],
) -> None:
    members: list[tuple[tarfile.TarInfo, bytes | None]] = []
    with tarfile.open(archive_path, "r:gz") as source:
        for member in source.getmembers():
            extracted = source.extractfile(member) if member.isfile() else None
            members.append((member, extracted.read() if extracted else None))
    mutate(members)
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", filename="", mtime=EPOCH) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as target:
            for member, value in members:
                target.addfile(member, io.BytesIO(value) if value is not None else None)
    archive_path.write_bytes(buffer.getvalue())


def test_build_is_deterministic_and_verify_is_explicitly_non_promotable(
    tmp_path: Path,
) -> None:
    first_source, first_wheel, first_evidence = _source(tmp_path / "first")
    second_source, second_wheel, second_evidence = _source(tmp_path / "second")
    arguments = {
        "source_commit": COMMIT,
        "source_date_epoch": EPOCH,
        "enforce_clean_source": False,
    }
    first = build_bundle(
        source_root=first_source,
        wheel_path=first_wheel,
        evidence_path=first_evidence,
        output_directory=tmp_path / "out-one",
        **arguments,
    )
    second = build_bundle(
        source_root=second_source,
        wheel_path=second_wheel,
        evidence_path=second_evidence,
        output_directory=tmp_path / "out-two",
        **arguments,
    )

    assert first.read_bytes() == second.read_bytes()
    assert verify_bundle(first) == {
        "bundle_format_version": 1,
        "source_commit": COMMIT,
        "package_version": VERSION,
        "migration_head": "20260826_0042",
        "integrity": "verified",
        "signature": "not_verified",
        "promotable": False,
    }


def test_verifier_rejects_modified_content_with_stale_checksum(tmp_path: Path) -> None:
    archive = _build(tmp_path)

    def mutate(members: list[tuple[tarfile.TarInfo, bytes | None]]) -> None:
        for index, (member, value) in enumerate(members):
            if member.name.endswith("/runbooks/user-lifecycle.md"):
                replacement = b"changed\n"
                member.size = len(replacement)
                members[index] = (member, replacement)
                return
        raise AssertionError("fixture payload absent")

    _rewrite(archive, mutate)
    with pytest.raises(BundleRejected, match="operational release bundle rejected"):
        verify_bundle(archive)


def test_verifier_rejects_unknown_empty_directory(tmp_path: Path) -> None:
    archive = _build(tmp_path)

    def mutate(members: list[tuple[tarfile.TarInfo, bytes | None]]) -> None:
        root = members[0][0].name.rstrip("/").split("/")[0]
        info = tarfile.TarInfo(f"{root}/unknown/")
        info.type = tarfile.DIRTYPE
        info.mode = 0o755
        info.uid = info.gid = 0
        info.mtime = EPOCH
        members.append((info, None))

    _rewrite(archive, mutate)
    with pytest.raises(BundleRejected):
        verify_bundle(archive)


def test_builder_rejects_secret_shaped_payload_without_output(tmp_path: Path) -> None:
    source, wheel, evidence = _source(tmp_path)
    (source / "operations/runbooks" / RUNBOOKS[0]).write_text(
        "-----BEGIN PRIVATE KEY-----\n", encoding="utf-8"
    )
    output = tmp_path / "output"

    with pytest.raises(BundleRejected):
        build_bundle(
            source_root=source,
            wheel_path=wheel,
            evidence_path=evidence,
            output_directory=output,
            source_commit=COMMIT,
            source_date_epoch=EPOCH,
            enforce_clean_source=False,
        )
    assert not output.exists()


def test_builder_rejects_wrong_wheel_name_and_disconnected_migrations(
    tmp_path: Path,
) -> None:
    source, wheel, evidence = _source(tmp_path)
    renamed = wheel.with_name("runtime.whl")
    wheel.rename(renamed)
    with pytest.raises(BundleRejected):
        build_bundle(
            source_root=source,
            wheel_path=renamed,
            evidence_path=evidence,
            output_directory=tmp_path / "wrong-name",
            source_commit=COMMIT,
            source_date_epoch=EPOCH,
            enforce_clean_source=False,
        )
    _wheel(renamed, disconnected=True)
    valid_name = renamed.with_name(f"liquent-{VERSION}-py3-none-any.whl")
    renamed.rename(valid_name)
    with pytest.raises(BundleRejected):
        build_bundle(
            source_root=source,
            wheel_path=valid_name,
            evidence_path=evidence,
            output_directory=tmp_path / "bad-chain",
            source_commit=COMMIT,
            source_date_epoch=EPOCH,
            enforce_clean_source=False,
        )


def test_normal_builder_rejects_dirty_git_source(tmp_path: Path) -> None:
    source, wheel, evidence = _source(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    subprocess.run(["git", "add", "."], cwd=source, check=True)
    subprocess.run(
        [
            "git", "-c", "user.name=Bundle Test", "-c",
            "user.email=bundle@example.invalid", "commit", "-qm", "fixture",
        ],
        cwd=source,
        check=True,
    )
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=source, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    evidence_data = json.loads(evidence.read_text(encoding="utf-8"))
    evidence_data["source_commit"] = commit
    evidence.write_text(json.dumps(evidence_data), encoding="utf-8")

    with pytest.raises(BundleRejected):
        build_bundle(
            source_root=source,
            wheel_path=wheel,
            evidence_path=evidence,
            output_directory=tmp_path / "dirty",
            source_commit=commit,
            source_date_epoch=EPOCH,
        )
    assert not (tmp_path / "dirty").exists()


def test_existing_output_is_never_overwritten(tmp_path: Path) -> None:
    archive = _build(tmp_path)
    original = archive.read_bytes()
    source, wheel, evidence = _source(tmp_path / "again")
    with pytest.raises(BundleRejected):
        build_bundle(
            source_root=source,
            wheel_path=wheel,
            evidence_path=evidence,
            output_directory=archive.parent,
            source_commit=COMMIT,
            source_date_epoch=EPOCH,
            enforce_clean_source=False,
        )
    assert archive.read_bytes() == original


def test_cli_returns_detail_limited_rejection(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    invalid = tmp_path / "invalid.tar.gz"
    invalid.write_bytes(b"not an archive")

    assert main(["verify", "--bundle", str(invalid)]) == 2
    assert json.loads(capsys.readouterr().out) == {
        "error": "operational_release_bundle_rejected"
    }
