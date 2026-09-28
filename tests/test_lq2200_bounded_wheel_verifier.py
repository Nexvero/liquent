from pathlib import Path
import base64
from hashlib import sha256
import tomllib
import zipfile

import pytest

from tools import verify_release_wheel as verifier


def _write_member(archive: zipfile.ZipFile, name: str, payload: bytes, *, mode: int | None = None) -> None:
    info = zipfile.ZipInfo(name)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = ((0o100664 if name.endswith(".dist-info/RECORD") else 0o100644) if mode is None else mode) << 16
    archive.writestr(info, payload)


def _valid_wheel(
    path: Path,
    *,
    dist_version: str = "0.0.1",
    metadata_name: str = "liquent",
    metadata_version: str = "0.0.1",
    core_metadata_version: str = "2.4",
    tag: str = "py3-none-any",
    generator: str = "setuptools (80.10.2)",
    duplicate_generator: bool = False,
    requires_python: str = ">=3.10",
    license_expression: str = "LicenseRef-Proprietary",
    requires_dist: list[str] | None = None,
    provides_extra: list[str] | None = None,
    additional_metadata: str = "",
    entry_points: dict[str, str] | None = None,
    additional_member: tuple[str, bytes] | None = None,
    record_hash_override: str | None = None,
    record_size_override: str | None = None,
    omit_record_for: str | None = None,
) -> None:
    dist_info = f"liquent-{dist_version}.dist-info"
    if entry_points is None:
        project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
        entry_points = project["project"]["scripts"]
    entry_point_payload = (
        "[console_scripts]\n"
        + "".join(
            f"{name} = {target}\n" for name, target in sorted(entry_points.items())
        )
    ).encode()
    payloads: list[tuple[str, bytes]] = [
        (name, b"required\n") for name in sorted(verifier.REQUIRED_FILES)
    ]
    payloads.append(("liquent/__init__.py", b""))
    payloads.extend(
        [
            (
                f"{dist_info}/entry_points.txt",
                entry_point_payload,
            ),
            (
                f"{dist_info}/METADATA",
                f"Metadata-Version: {core_metadata_version}\nName: {metadata_name}\nVersion: {metadata_version}\n\n".encode(),
            ),
            (
                f"{dist_info}/WHEEL",
                (
                    f"Wheel-Version: 1.0\nGenerator: {generator}\n"
                    + (f"Generator: {generator}\n" if duplicate_generator else "")
                    + f"Root-Is-Purelib: true\nTag: {tag}\n\n"
                ).encode(),
            ),
        ]
    )
    record_name = f"{dist_info}/RECORD"
    dependency_headers = "".join(
        f"Requires-Dist: {requirement}\n"
        for requirement in (
            verifier.EXPECTED_REQUIRES_DIST if requires_dist is None else requires_dist
        )
    )
    extra_headers = "".join(
        f"Provides-Extra: {extra}\n"
        for extra in (["dev", "visual"] if provides_extra is None else provides_extra)
    )
    metadata_payload = (
        f"Metadata-Version: {core_metadata_version}\n"
        f"Name: {metadata_name}\n"
        f"Version: {metadata_version}\n"
        f"License-Expression: {license_expression}\n"
        f"Requires-Python: {requires_python}\n"
        f"{dependency_headers}{extra_headers}{additional_metadata}\n"
    ).encode()
    payloads = [
        (name, metadata_payload if name == f"{dist_info}/METADATA" else payload)
        for name, payload in payloads
    ]
    payloads.append((f"{dist_info}/top_level.txt", b"liquent\nliquent_platform\n"))
    if additional_member is not None:
        payloads.append(additional_member)
    record_rows = []
    for name, payload in payloads:
        if name == omit_record_for:
            continue
        digest = "sha256=" + base64.urlsafe_b64encode(sha256(payload).digest()).rstrip(b"=").decode()
        if record_hash_override is not None and not record_rows:
            digest = record_hash_override
        size = str(len(payload))
        if record_size_override is not None and not record_rows:
            size = record_size_override
        record_rows.append(f"{name},{digest},{size}")
    record_rows.append(f"{record_name},,")
    payloads.append((record_name, ("\n".join(record_rows) + "\n").encode()))
    with zipfile.ZipFile(path, "w") as archive:
        for name, payload in payloads:
            _write_member(archive, name, payload)


def test_bounded_verifier_accepts_canonical_wheel(tmp_path: Path) -> None:
    wheel = tmp_path / "liquent-0.0.1-py3-none-any.whl"
    _valid_wheel(wheel)
    assert len(verifier.verify_wheel(wheel)) == 64


def test_bounded_verifier_rejects_symlink_without_following_it(tmp_path: Path) -> None:
    wheel = tmp_path / "liquent-0.0.1-py3-none-any.whl"
    _valid_wheel(wheel)
    alias = tmp_path / "alias.whl"
    alias.symlink_to(wheel)
    with pytest.raises(ValueError):
        verifier.verify_wheel(alias)


@pytest.mark.parametrize("name", ["/absolute", "../escape", "a//alias", "a\\windows", "cafe\u0301"])
def test_member_gate_rejects_unsafe_or_noncanonical_names(name: str) -> None:
    info = zipfile.ZipInfo(name)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    with pytest.raises(ValueError, match="wheel verification failed"):
        verifier._validate_wheel_members([info])


def test_member_gate_rejects_duplicate_names() -> None:
    first = zipfile.ZipInfo("package/file.py")
    first.compress_type = zipfile.ZIP_DEFLATED
    first.create_system = 3
    first.external_attr = 0o100644 << 16
    second = zipfile.ZipInfo("package/file.py")
    second.compress_type = zipfile.ZIP_DEFLATED
    second.create_system = 3
    second.external_attr = 0o100644 << 16
    with pytest.raises(ValueError, match="wheel verification failed"):
        verifier._validate_wheel_members([first, second])


@pytest.mark.parametrize("mode", [0o100600, 0o100755, 0o100777, 0o120777])
def test_member_gate_rejects_noncanonical_modes(mode: int) -> None:
    info = zipfile.ZipInfo("package/file.py")
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = mode << 16
    with pytest.raises(ValueError, match="wheel verification failed"):
        verifier._validate_wheel_members([info])


def test_member_gate_rejects_uncompressed_or_flagged_member() -> None:
    info = zipfile.ZipInfo("package/file.py")
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    with pytest.raises(ValueError, match="wheel verification failed"):
        verifier._validate_wheel_members([info])
    info.compress_type = zipfile.ZIP_DEFLATED
    info.flag_bits = 1
    with pytest.raises(ValueError, match="wheel verification failed"):
        verifier._validate_wheel_members([info])


def test_verifier_rejects_archive_over_bound(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wheel = tmp_path / "liquent-0.0.1-py3-none-any.whl"
    _valid_wheel(wheel)
    monkeypatch.setattr(verifier, "MAX_WHEEL_ARCHIVE_BYTES", wheel.stat().st_size - 1)
    with pytest.raises(ValueError):
        verifier.verify_wheel(wheel)


@pytest.mark.parametrize(
    "filename",
    [
        "other-0.0.1-py3-none-any.whl",
        "liquent-0.0.1-cp312-none-any.whl",
        "liquent-0.0.1-py3-none-linux.whl",
        "liquent--py3-none-any.whl",
    ],
)
def test_identity_gate_rejects_foreign_or_nonuniversal_filename(
    tmp_path: Path, filename: str
) -> None:
    wheel = tmp_path / filename
    _valid_wheel(wheel)
    with pytest.raises(ValueError, match="wheel identity verification failed"):
        verifier.verify_wheel(wheel)


@pytest.mark.parametrize(
    ("kwargs", "filename"),
    [
        ({"metadata_name": "other"}, "liquent-0.0.1-py3-none-any.whl"),
        ({"metadata_version": "0.0.2"}, "liquent-0.0.1-py3-none-any.whl"),
        ({"dist_version": "0.0.2"}, "liquent-0.0.1-py3-none-any.whl"),
        ({"tag": "cp312-none-any"}, "liquent-0.0.1-py3-none-any.whl"),
    ],
)
def test_identity_gate_rejects_mismatched_embedded_identity(
    tmp_path: Path, kwargs: dict[str, str], filename: str
) -> None:
    wheel = tmp_path / filename
    _valid_wheel(wheel, **kwargs)
    with pytest.raises(ValueError, match="wheel identity verification failed"):
        verifier.verify_wheel(wheel)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"record_hash_override": "sha256=invalid"},
        {"record_size_override": "999"},
        {"omit_record_for": "liquent_platform/persistence/alembic/env.py"},
    ],
)
def test_record_gate_rejects_hash_size_or_coverage_mismatch(
    tmp_path: Path, kwargs: dict[str, str]
) -> None:
    wheel = tmp_path / "liquent-0.0.1-py3-none-any.whl"
    _valid_wheel(wheel, **kwargs)
    with pytest.raises(ValueError, match="wheel RECORD verification failed"):
        verifier.verify_wheel(wheel)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"core_metadata_version": "2.3"},
        {"generator": "setuptools (80.10.1)"},
        {"generator": "other (80.10.2)"},
        {"duplicate_generator": True},
    ],
)
def test_metadata_gate_rejects_unbound_backend_identity(
    tmp_path: Path, kwargs: dict[str, object]
) -> None:
    wheel = tmp_path / "liquent-0.0.1-py3-none-any.whl"
    _valid_wheel(wheel, **kwargs)
    with pytest.raises(ValueError, match="wheel identity verification failed"):
        verifier.verify_wheel(wheel)


def test_metadata_parser_rejects_carriage_return_alias() -> None:
    with pytest.raises(ValueError, match="wheel metadata verification failed"):
        verifier._metadata_message(b"Name: liquent\r\n\r\n")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"requires_python": ">=3.9"},
        {"license_expression": "MIT"},
        {"requires_dist": verifier.EXPECTED_REQUIRES_DIST[:-1]},
        {"requires_dist": [*verifier.EXPECTED_REQUIRES_DIST, "unknown>=1"]},
        {"provides_extra": ["dev"]},
        {"provides_extra": ["visual", "dev"]},
        {"additional_metadata": "Requires-External: system-tool\n"},
        {"additional_metadata": "Dynamic: Requires-Dist\n"},
    ],
)
def test_metadata_gate_rejects_dependency_or_platform_drift(
    tmp_path: Path, kwargs: dict[str, object]
) -> None:
    wheel = tmp_path / "liquent-0.0.1-py3-none-any.whl"
    _valid_wheel(wheel, **kwargs)
    with pytest.raises(ValueError, match="wheel identity verification failed"):
        verifier.verify_wheel(wheel)


@pytest.mark.parametrize("mutation", ["missing", "additional", "target"])
def test_entry_point_gate_rejects_command_set_drift(
    tmp_path: Path, mutation: str
) -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    entries = dict(project["project"]["scripts"])
    if mutation == "missing":
        entries.pop(next(iter(entries)))
    elif mutation == "additional":
        entries["liquent-unreviewed"] = "liquent_platform.operators.runtime_inspect:main"
    else:
        entries["liquent-control-plane"] = "liquent_platform.operators.runtime_inspect:main"
    wheel = tmp_path / "liquent-0.0.1-py3-none-any.whl"
    _valid_wheel(wheel, entry_points=entries)
    with pytest.raises(ValueError, match="wheel entry-point verification failed"):
        verifier.verify_wheel(wheel)


@pytest.mark.parametrize(
    "raw",
    [
        b"[other]\nliquent-command = liquent_platform.module:main\n",
        b"[console_scripts]\r\n",
        b"[console_scripts]\nname = invalid target\n",
        b"[console_scripts]\nname = module:main\nname = module:other\n",
    ],
)
def test_entry_point_parser_rejects_noncanonical_structure(raw: bytes) -> None:
    with pytest.raises(ValueError, match="wheel entry-point verification failed"):
        verifier._verify_entry_points(raw)


def test_member_set_gate_rejects_foreign_top_level_root(tmp_path: Path) -> None:
    wheel = tmp_path / "liquent-0.0.1-py3-none-any.whl"
    _valid_wheel(wheel, additional_member=("foreign/module.py", b""))
    with pytest.raises(ValueError, match="wheel member-set verification failed"):
        verifier.verify_wheel(wheel)


def test_member_set_gate_rejects_release_count_or_digest_mismatch(tmp_path: Path) -> None:
    wheel = tmp_path / "liquent-0.0.1-py3-none-any.whl"
    _valid_wheel(wheel)
    with pytest.raises(ValueError, match="wheel member-set verification failed"):
        verifier.verify_wheel(
            wheel,
            expected_member_count=verifier.EXPECTED_WHEEL_MEMBER_COUNT,
            expected_member_set_sha256=verifier.EXPECTED_WHEEL_MEMBER_SET_SHA256,
        )


def test_member_set_gate_requires_count_and_digest_together(tmp_path: Path) -> None:
    wheel = tmp_path / "liquent-0.0.1-py3-none-any.whl"
    _valid_wheel(wheel)
    with pytest.raises(ValueError, match="wheel member-set verification failed"):
        verifier.verify_wheel(wheel, expected_member_count=1)


def _materialize_wheel_sources(wheel: Path, source_root: Path) -> None:
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if not (name.startswith("liquent/") or name.startswith("liquent_platform/")):
                continue
            target = source_root / "src" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))


def test_source_payload_gate_accepts_exact_source_tree(tmp_path: Path) -> None:
    wheel = tmp_path / "liquent-0.0.1-py3-none-any.whl"
    source_root = tmp_path / "source"
    _valid_wheel(wheel)
    _materialize_wheel_sources(wheel, source_root)
    assert verifier.verify_wheel(wheel, source_root=source_root)


@pytest.mark.parametrize("mutation", ["changed", "missing", "additional"])
def test_source_payload_gate_rejects_source_tree_drift(
    tmp_path: Path, mutation: str
) -> None:
    wheel = tmp_path / "liquent-0.0.1-py3-none-any.whl"
    source_root = tmp_path / "source"
    _valid_wheel(wheel)
    _materialize_wheel_sources(wheel, source_root)
    candidate = source_root / "src/liquent/__init__.py"
    if mutation == "changed":
        candidate.write_bytes(b"changed")
    elif mutation == "missing":
        candidate.unlink()
    else:
        (source_root / "src/liquent/additional.py").write_bytes(b"")
    with pytest.raises(ValueError, match="wheel source-payload verification failed"):
        verifier.verify_wheel(wheel, source_root=source_root)


def test_source_payload_gate_rejects_symlinked_package_root(tmp_path: Path) -> None:
    wheel = tmp_path / "liquent-0.0.1-py3-none-any.whl"
    source_root = tmp_path / "source"
    _valid_wheel(wheel)
    _materialize_wheel_sources(wheel, source_root)
    package = source_root / "src/liquent"
    moved = source_root / "liquent-moved"
    package.rename(moved)
    package.symlink_to(moved, target_is_directory=True)
    with pytest.raises(ValueError, match="wheel source-payload verification failed"):
        verifier.verify_wheel(wheel, source_root=source_root)


def _canonical_info(name: str = "package/file.py") -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(2026, 9, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.create_version = 20
    info.extract_version = 20
    info.external_attr = 0o100644 << 16
    return info


def test_zip_metadata_gate_accepts_uniform_canonical_members() -> None:
    verifier._validate_wheel_zip_metadata(
        [_canonical_info(), _canonical_info("package/other.py")],
        archive_comment=b"",
    )


def test_canonical_wheel_renderer_reproduces_wheel_bytes(tmp_path: Path) -> None:
    wheel = tmp_path / "liquent-0.0.1-py3-none-any.whl"
    _valid_wheel(wheel)
    with zipfile.ZipFile(wheel) as archive:
        infos = archive.infolist()
        payloads = {info.filename: archive.read(info) for info in infos}

    assert verifier._render_canonical_wheel(infos, payloads) == wheel.read_bytes()


def test_wheel_gate_rejects_alternate_valid_deflate_streams(tmp_path: Path) -> None:
    wheel = tmp_path / "liquent-0.0.1-py3-none-any.whl"
    _valid_wheel(wheel)
    with zipfile.ZipFile(wheel) as archive:
        infos = archive.infolist()
        payloads = {info.filename: archive.read(info) for info in infos}
    alternate = tmp_path / "alternate.whl"
    with zipfile.ZipFile(
        alternate, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1
    ) as archive:
        for info in infos:
            info._compresslevel = 1
            archive.writestr(info, payloads[info.filename])
    wheel.write_bytes(alternate.read_bytes())

    with zipfile.ZipFile(wheel) as archive:
        assert {name: archive.read(name) for name in archive.namelist()} == payloads
    with pytest.raises(ValueError, match="wheel compressed-byte verification failed"):
        verifier.verify_wheel(wheel)


@pytest.mark.parametrize(
    ("attribute", "value"),
    [
        ("create_system", 0),
        ("create_version", 45),
        ("extract_version", 45),
        ("reserved", 1),
        ("volume", 1),
        ("internal_attr", 1),
        ("extra", b"unreviewed"),
        ("comment", b"unreviewed"),
    ],
)
def test_zip_metadata_gate_rejects_noncanonical_member_metadata(
    attribute: str, value: int | bytes
) -> None:
    info = _canonical_info()
    setattr(info, attribute, value)
    with pytest.raises(ValueError, match="wheel ZIP metadata verification failed"):
        verifier._validate_wheel_zip_metadata([info], archive_comment=b"")


def test_zip_metadata_gate_rejects_archive_comment() -> None:
    with pytest.raises(ValueError, match="wheel ZIP metadata verification failed"):
        verifier._validate_wheel_zip_metadata(
            [_canonical_info()], archive_comment=b"unreviewed"
        )


def test_zip_metadata_gate_rejects_nonuniform_or_odd_second_timestamps() -> None:
    first = _canonical_info()
    second = _canonical_info("package/other.py")
    second.date_time = (2026, 9, 1, 0, 0, 2)
    with pytest.raises(ValueError, match="wheel ZIP metadata verification failed"):
        verifier._validate_wheel_zip_metadata([first, second], archive_comment=b"")
    first.date_time = (2026, 9, 1, 0, 0, 1)
    with pytest.raises(ValueError, match="wheel ZIP metadata verification failed"):
        verifier._validate_wheel_zip_metadata([first], archive_comment=b"")


def test_epoch_binding_rounds_only_to_zip_two_second_resolution() -> None:
    assert verifier._wheel_timestamp_from_epoch(1788220801) == (2026, 9, 1, 0, 0, 0)


@pytest.mark.parametrize("epoch", [0, 315532799, -1, True, 0x100000000])
def test_epoch_binding_rejects_values_outside_wheel_range(epoch: int) -> None:
    with pytest.raises(ValueError, match="wheel timestamp verification failed"):
        verifier._wheel_timestamp_from_epoch(epoch)


def test_verifier_binds_member_timestamp_to_source_date_epoch(tmp_path: Path) -> None:
    wheel = tmp_path / "liquent-0.0.1-py3-none-any.whl"
    _valid_wheel(wheel)
    assert verifier.verify_wheel(wheel, source_date_epoch=315532800)
    with pytest.raises(ValueError, match="wheel ZIP metadata verification failed"):
        verifier.verify_wheel(wheel, source_date_epoch=1788220800)
