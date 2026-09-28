from pathlib import Path
import gzip
import io
import tarfile
import zlib

import pytest

from tools.local_release_preflight_gates import (
    CommandResult,
    GENERATED_SDIST_FILES,
    EXPECTED_SDIST_REQUIRES,
    EXPECTED_SDIST_SETUP_CFG,
    EXPECTED_SDIST_GZIP_OS,
    EXPECTED_SDIST_GZIP_XFL,
    LocalGateContext,
    LocalGateRejected,
    MAX_SOURCE_DATE_EPOCH,
    MAX_SDIST_FILE_BYTES,
    MAX_SDIST_MEMBER_COUNT,
    MAX_SDIST_MEMBER_NAME_BYTES,
    MAX_SDIST_TOTAL_FILE_BYTES,
    MAX_SDIST_UNCOMPRESSED_BYTES,
    SdistGate,
    _normalize_sdist,
    _private_output_directory_identity,
    _canonical,
    _distribution_pair_identity,
    _render_canonical_sdist_tar,
    _render_canonical_sdist_gzip,
    _quality_evidence_facts,
    _sha256,
    _sdist_root_from_filename,
    _verify_normalized_sdist,
    _verify_distribution_pair,
    _verify_sdist_source_payloads,
    _validate_sdist_generated_payloads,
    _validate_sdist_member_names,
    _validate_sdist_tar_envelope,
)


def _write_sdist(path: Path, root: Path, *, mtime: int, value: int = 1) -> None:
    source = root / "liquent-0.0.1"
    source.mkdir(parents=True)
    (source / "pyproject.toml").write_text("[project]\nname='liquent'\n", encoding="utf-8")
    (source / "module.py").write_text(f"VALUE = {value}\n", encoding="utf-8")
    package = source / "src" / "liquent_platform"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    with tarfile.open(path, "w:gz") as archive:
        for item in [source, *sorted(source.rglob("*"))]:
            info = archive.gettarinfo(item, arcname=str(item.relative_to(root)))
            info.mtime = mtime
            if item.is_file():
                with item.open("rb") as payload:
                    archive.addfile(info, payload)
            else:
                archive.addfile(info)


def test_normalizer_produces_identical_bytes_from_distinct_build_times(tmp_path: Path) -> None:
    first = tmp_path / "first" / "liquent-0.0.1.tar.gz"
    second = tmp_path / "second" / "liquent-0.0.1.tar.gz"
    first.parent.mkdir()
    second.parent.mkdir()
    _write_sdist(first, tmp_path / "a", mtime=100)
    _write_sdist(second, tmp_path / "b", mtime=200)

    _normalize_sdist(first, "1788220800")
    _normalize_sdist(second, "1788220800")

    assert first.read_bytes() == second.read_bytes()


def test_normalizer_preserves_names_and_payloads_and_sets_fixed_metadata(tmp_path: Path) -> None:
    archive_path = tmp_path / "liquent-0.0.1.tar.gz"
    _write_sdist(archive_path, tmp_path / "source", mtime=100)

    _normalize_sdist(archive_path, "1788220800")

    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        payload = archive.extractfile("liquent-0.0.1/module.py")
        assert payload is not None and payload.read() == b"VALUE = 1\n"
    assert [member.name for member in members] == sorted(member.name for member in members)
    assert all(member.mtime == 1788220800 for member in members)
    assert all((member.uid, member.gid, member.uname, member.gname) == (0, 0, "", "") for member in members)


@pytest.mark.parametrize("epoch", ["", "0", "-1", "value", str(MAX_SOURCE_DATE_EPOCH + 1)])
def test_normalizer_rejects_invalid_source_date_epoch(tmp_path: Path, epoch: str) -> None:
    archive_path = tmp_path / "liquent-0.0.1.tar.gz"
    _write_sdist(archive_path, tmp_path / "source", mtime=100)

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _normalize_sdist(archive_path, epoch)


def test_distribution_gate_normalizes_sdist_before_recording_hash() -> None:
    source = Path("tools/local_release_preflight_gates.py").read_text(encoding="utf-8")
    distribution_gate = source[source.index("class DistributionsGate") : source.index("class WheelGate")]
    assert '_normalize_sdist(sdists[0], epoch)' in distribution_gate
    assert distribution_gate.index("_normalize_sdist") < distribution_gate.index("self.context.wheel")


@pytest.mark.parametrize(
    "names",
    [
        ("/absolute",),
        ("liquent/../escape",),
        ("liquent//alias",),
        ("liquent\\windows",),
        ("liquent/a", "liquent/a"),
        ("liquent/a", "second/a"),
    ],
)
def test_member_name_gate_rejects_unsafe_or_ambiguous_topology(names: tuple[str, ...]) -> None:
    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _validate_sdist_member_names([tarfile.TarInfo(name) for name in names])


def test_rejected_archive_remains_unchanged_and_leaves_no_temporary_file(tmp_path: Path) -> None:
    archive_path = tmp_path / "liquent-0.0.1.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.addfile(tarfile.TarInfo("../escape"))
    original = archive_path.read_bytes()

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _normalize_sdist(archive_path, "1788220800")

    assert archive_path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [archive_path]


def test_member_gate_rejects_excessive_count() -> None:
    members = [tarfile.TarInfo(f"liquent/{index}") for index in range(MAX_SDIST_MEMBER_COUNT + 1)]
    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _validate_sdist_member_names(members)


def test_member_gate_rejects_excessive_utf8_name_length() -> None:
    member = tarfile.TarInfo("liquent/" + "ä" * MAX_SDIST_MEMBER_NAME_BYTES)
    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _validate_sdist_member_names([member])


@pytest.mark.parametrize("size", [MAX_SDIST_FILE_BYTES + 1, -1])
def test_member_gate_rejects_invalid_individual_file_size(size: int) -> None:
    member = tarfile.TarInfo("liquent/file")
    member.type = tarfile.REGTYPE
    member.size = size
    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _validate_sdist_member_names([member])


def test_member_gate_rejects_excessive_total_file_size() -> None:
    members = []
    remaining = MAX_SDIST_TOTAL_FILE_BYTES + 1
    index = 0
    while remaining:
        member = tarfile.TarInfo(f"liquent/{index}")
        member.type = tarfile.REGTYPE
        member.size = min(MAX_SDIST_FILE_BYTES, remaining)
        members.append(member)
        remaining -= member.size
        index += 1
    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _validate_sdist_member_names(members)


def test_normalizer_rejects_symlink_input_without_following_it(tmp_path: Path) -> None:
    archive_path = tmp_path / "liquent-0.0.1.tar.gz"
    _write_sdist(archive_path, tmp_path / "source", mtime=100)
    alias = tmp_path / "alias.tar.gz"
    alias.symlink_to(archive_path)

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _normalize_sdist(alias, "1788220800")

    assert archive_path.is_file()


@pytest.mark.parametrize(
    "name",
    [
        "source.tar.gz",
        "liquent-.tar.gz",
        "other-0.0.1.tar.gz",
        "liquent-/0.0.1.tar.gz",
        "liquent- version.tar.gz",
    ],
)
def test_sdist_filename_gate_rejects_unbound_names(name: str) -> None:
    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _sdist_root_from_filename(Path(name))


def test_sdist_filename_gate_derives_exact_package_root() -> None:
    assert _sdist_root_from_filename(Path("liquent-1.2.3rc1+build.tar.gz")) == "liquent-1.2.3rc1+build"


def test_member_gate_binds_root_directory_to_artifact_name() -> None:
    root = tarfile.TarInfo("liquent-0.0.1")
    root.type = tarfile.DIRTYPE
    root.mode = 0o755
    file = tarfile.TarInfo("liquent-0.0.1/file.py")
    _validate_sdist_member_names([root, file], expected_root="liquent-0.0.1")


def test_member_gate_rejects_missing_or_mismatched_expected_root() -> None:
    file = tarfile.TarInfo("liquent-0.0.1/file.py")
    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _validate_sdist_member_names([file], expected_root="liquent-0.0.1")
    root = tarfile.TarInfo("liquent-0.0.2")
    root.type = tarfile.DIRTYPE
    root.mode = 0o755
    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _validate_sdist_member_names([root], expected_root="liquent-0.0.1")


@pytest.mark.parametrize(
    "name",
    [
        "liquent/cafe\u0301.py",
        "liquent/zero\u200bwidth.py",
        "liquent/bidi\u202etxt.py",
        "liquent/control\x1f.py",
    ],
)
def test_member_gate_rejects_noncanonical_or_control_unicode_names(name: str) -> None:
    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _validate_sdist_member_names([tarfile.TarInfo(name)])


@pytest.mark.parametrize("mode", [0o600, 0o640, 0o755, 0o1644, 0o2644, 0o4644])
def test_member_gate_rejects_noncanonical_regular_file_mode(mode: int) -> None:
    member = tarfile.TarInfo("liquent/file.py")
    member.mode = mode
    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _validate_sdist_member_names([member])


@pytest.mark.parametrize("mode", [0o700, 0o744, 0o777, 0o1755, 0o2755, 0o4755])
def test_member_gate_rejects_noncanonical_directory_mode(mode: int) -> None:
    member = tarfile.TarInfo("liquent/package")
    member.type = tarfile.DIRTYPE
    member.mode = mode
    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _validate_sdist_member_names([member])


def test_member_gate_accepts_exact_long_path_pax_header() -> None:
    member = tarfile.TarInfo("liquent/" + "a" * 120)
    member.pax_headers = {"path": member.name}
    _validate_sdist_member_names([member])


def test_member_gate_accepts_bounded_source_mtime_for_later_discard() -> None:
    member = tarfile.TarInfo("liquent/file.py")
    member.pax_headers = {"mtime": "1788324698.3584907"}
    _validate_sdist_member_names([member])


@pytest.mark.parametrize(
    "headers",
    [
        {"path": "liquent/other.py"},
        {"comment": "unreviewed"},
        {"SCHILY.xattr.user.value": "unreviewed"},
        {"mtime": "NaN"},
        {"mtime": "Infinity"},
        {"mtime": "-1"},
        {"mtime": "253402300800"},
    ],
)
def test_member_gate_rejects_unbound_or_unknown_pax_metadata(headers: dict[str, str]) -> None:
    member = tarfile.TarInfo("liquent/file.py")
    member.pax_headers = headers
    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _validate_sdist_member_names([member])


def test_normalized_output_verifier_accepts_matching_manifest(tmp_path: Path) -> None:
    archive_path = tmp_path / "liquent-0.0.1.tar.gz"
    _write_sdist(archive_path, tmp_path / "source", mtime=100)
    _normalize_sdist(archive_path, "1788220800")
    with tarfile.open(archive_path, "r:gz") as archive:
        entries = []
        for member in archive:
            payload = archive.extractfile(member).read() if member.isfile() else None
            entries.append((member, payload))

    from tools.local_release_preflight_gates import _sdist_manifest

    _verify_normalized_sdist(
        archive_path,
        expected_root="liquent-0.0.1",
        epoch=1788220800,
        expected_manifest=_sdist_manifest(entries),
    )


def test_normalizer_writes_canonical_complete_gzip_header(tmp_path: Path) -> None:
    archive_path = tmp_path / "liquent-0.0.1.tar.gz"
    _write_sdist(archive_path, tmp_path / "source", mtime=100)
    _normalize_sdist(archive_path, "1788220800")

    assert archive_path.read_bytes()[:10] == (
        b"\x1f\x8b\x08\x00\x80\x15\x96\x6a"
        + bytes((EXPECTED_SDIST_GZIP_XFL, EXPECTED_SDIST_GZIP_OS))
    )


@pytest.mark.parametrize(("offset", "value"), [(8, 0), (9, 3)])
def test_normalized_output_verifier_rejects_noncanonical_gzip_header(
    tmp_path: Path, offset: int, value: int
) -> None:
    archive_path = tmp_path / "liquent-0.0.1.tar.gz"
    _write_sdist(archive_path, tmp_path / "source", mtime=100)
    manifest = _normalize_sdist(archive_path, "1788220800")
    payload = bytearray(archive_path.read_bytes())
    payload[offset] = value
    archive_path.write_bytes(payload)

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _verify_normalized_sdist(
            archive_path,
            expected_root="liquent-0.0.1",
            epoch=1788220800,
            expected_manifest=manifest,
        )


def test_normalized_output_verifier_rejects_corrupt_gzip_trailer(tmp_path: Path) -> None:
    archive_path = tmp_path / "liquent-0.0.1.tar.gz"
    _write_sdist(archive_path, tmp_path / "source", mtime=100)
    manifest = _normalize_sdist(archive_path, "1788220800")
    payload = bytearray(archive_path.read_bytes())
    payload[-8] ^= 1
    archive_path.write_bytes(payload)

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _verify_normalized_sdist(
            archive_path,
            expected_root="liquent-0.0.1",
            epoch=1788220800,
            expected_manifest=manifest,
        )


def test_normalized_output_verifier_bounds_uncompressed_gzip_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive_path = tmp_path / "liquent-0.0.1.tar.gz"
    _write_sdist(archive_path, tmp_path / "source", mtime=100)
    manifest = _normalize_sdist(archive_path, "1788220800")
    monkeypatch.setattr(
        "tools.local_release_preflight_gates.MAX_SDIST_UNCOMPRESSED_BYTES", 1
    )

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _verify_normalized_sdist(
            archive_path,
            expected_root="liquent-0.0.1",
            epoch=1788220800,
            expected_manifest=manifest,
        )

    assert MAX_SDIST_UNCOMPRESSED_BYTES == 40 * 1024 * 1024


def _rewrite_gzip_payload(path: Path, payload: bytes) -> None:
    buffer = io.BytesIO()
    with gzip.GzipFile(
        filename="", mode="wb", fileobj=buffer, mtime=1788220800
    ) as compressed:
        compressed.write(payload)
    path.write_bytes(buffer.getvalue())


def test_normalized_output_verifier_rejects_concatenated_gzip_member(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "liquent-0.0.1.tar.gz"
    _write_sdist(archive_path, tmp_path / "source", mtime=100)
    manifest = _normalize_sdist(archive_path, "1788220800")
    extra = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=extra, mtime=1788220800) as member:
        member.write(b"extra")
    archive_path.write_bytes(archive_path.read_bytes() + extra.getvalue())

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _verify_normalized_sdist(
            archive_path,
            expected_root="liquent-0.0.1",
            epoch=1788220800,
            expected_manifest=manifest,
        )


def test_tar_envelope_gate_accepts_minimal_record_padding(tmp_path: Path) -> None:
    archive_path = tmp_path / "liquent-0.0.1.tar.gz"
    _write_sdist(archive_path, tmp_path / "source", mtime=100)
    _normalize_sdist(archive_path, "1788220800")
    with gzip.open(archive_path, "rb") as compressed:
        tar_bytes = compressed.read()
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()

    _validate_sdist_tar_envelope(tar_bytes, members)
    assert len(tar_bytes) % tarfile.RECORDSIZE == 0


@pytest.mark.parametrize("mutation", ["extra_record", "nonzero_padding"])
def test_normalized_output_verifier_rejects_noncanonical_tar_envelope(
    tmp_path: Path, mutation: str
) -> None:
    archive_path = tmp_path / "liquent-0.0.1.tar.gz"
    _write_sdist(archive_path, tmp_path / "source", mtime=100)
    manifest = _normalize_sdist(archive_path, "1788220800")
    with gzip.open(archive_path, "rb") as compressed:
        tar_payload = bytearray(compressed.read())
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
    logical_end = max(
        member.offset_data
        + ((member.size + tarfile.BLOCKSIZE - 1) // tarfile.BLOCKSIZE)
        * tarfile.BLOCKSIZE
        for member in members
    )
    if mutation == "extra_record":
        tar_payload.extend(bytes(tarfile.RECORDSIZE))
    else:
        tar_payload[logical_end + 2 * tarfile.BLOCKSIZE] = 1
    _rewrite_gzip_payload(archive_path, bytes(tar_payload))

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _verify_normalized_sdist(
            archive_path,
            expected_root="liquent-0.0.1",
            epoch=1788220800,
            expected_manifest=manifest,
        )


def test_canonical_tar_renderer_reproduces_normalized_raw_bytes(tmp_path: Path) -> None:
    archive_path = tmp_path / "liquent-0.0.1.tar.gz"
    _write_sdist(archive_path, tmp_path / "source", mtime=100)
    _normalize_sdist(archive_path, "1788220800")
    with tarfile.open(archive_path, "r:gz") as archive:
        entries = []
        for member in archive:
            payload = archive.extractfile(member).read() if member.isfile() else None
            entries.append((member, payload))
    with gzip.open(archive_path, "rb") as compressed:
        tar_bytes = compressed.read()

    assert _render_canonical_sdist_tar(entries, epoch=1788220800) == tar_bytes


def test_normalized_output_verifier_rejects_alternate_tar_checksum_encoding(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "liquent-0.0.1.tar.gz"
    _write_sdist(archive_path, tmp_path / "source", mtime=100)
    manifest = _normalize_sdist(archive_path, "1788220800")
    with gzip.open(archive_path, "rb") as compressed:
        tar_payload = bytearray(compressed.read())
    tar_payload[148:156] = b"        "
    checksum = sum(tar_payload[:512])
    tar_payload[148:156] = f"{checksum:07o}\0".encode("ascii")
    _rewrite_gzip_payload(archive_path, bytes(tar_payload))

    with tarfile.open(archive_path, "r:gz") as archive:
        assert archive.getmembers()
    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _verify_normalized_sdist(
            archive_path,
            expected_root="liquent-0.0.1",
            epoch=1788220800,
            expected_manifest=manifest,
        )


def test_canonical_gzip_renderer_reproduces_normalized_raw_bytes(tmp_path: Path) -> None:
    archive_path = tmp_path / "liquent-0.0.1.tar.gz"
    _write_sdist(archive_path, tmp_path / "source", mtime=100)
    _normalize_sdist(archive_path, "1788220800")
    with gzip.open(archive_path, "rb") as compressed:
        tar_bytes = compressed.read()

    assert (
        _render_canonical_sdist_gzip(tar_bytes, epoch=1788220800)
        == archive_path.read_bytes()
    )


def test_normalized_output_verifier_rejects_alternate_valid_deflate_stream(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "liquent-0.0.1.tar.gz"
    _write_sdist(archive_path, tmp_path / "source", mtime=100)
    manifest = _normalize_sdist(archive_path, "1788220800")
    with gzip.open(archive_path, "rb") as compressed:
        tar_bytes = compressed.read()
    encoder = zlib.compressobj(level=8, wbits=-15)
    deflate = encoder.compress(tar_bytes) + encoder.flush()
    header = b"\x1f\x8b\x08\x00" + (1788220800).to_bytes(4, "little") + b"\x02\xff"
    trailer = (zlib.crc32(tar_bytes) & 0xFFFFFFFF).to_bytes(4, "little") + (
        len(tar_bytes) & 0xFFFFFFFF
    ).to_bytes(4, "little")
    archive_path.write_bytes(header + deflate + trailer)

    with gzip.open(archive_path, "rb") as compressed:
        assert compressed.read() == tar_bytes
    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _verify_normalized_sdist(
            archive_path,
            expected_root="liquent-0.0.1",
            epoch=1788220800,
            expected_manifest=manifest,
        )


def test_normalized_output_verifier_rejects_manifest_mismatch(tmp_path: Path) -> None:
    archive_path = tmp_path / "liquent-0.0.1.tar.gz"
    _write_sdist(archive_path, tmp_path / "source", mtime=100)
    _normalize_sdist(archive_path, "1788220800")

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _verify_normalized_sdist(
            archive_path,
            expected_root="liquent-0.0.1",
            epoch=1788220800,
            expected_manifest=(),
        )


def test_normalized_output_verifier_rejects_wrong_epoch(tmp_path: Path) -> None:
    archive_path = tmp_path / "liquent-0.0.1.tar.gz"
    _write_sdist(archive_path, tmp_path / "source", mtime=100)
    _normalize_sdist(archive_path, "1788220800")

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _verify_normalized_sdist(
            archive_path,
            expected_root="liquent-0.0.1",
            epoch=1788220801,
            expected_manifest=(),
        )


def test_sdist_gate_rechecks_manifest_bound_by_distribution_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive_path = tmp_path / "liquent-0.0.1.tar.gz"
    _write_sdist(archive_path, tmp_path / "source", mtime=100)
    manifest = _normalize_sdist(archive_path, "1788220800")
    wheel = tmp_path / "liquent-0.0.1-py3-none-any.whl"
    wheel.write_bytes(b"canonical-wheel")

    def command_runner(argv: tuple[str, ...], *_: object) -> CommandResult:
        if "build" in argv:
            outdir = Path(argv[argv.index("--outdir") + 1])
            (outdir / wheel.name).write_bytes(wheel.read_bytes())
        return CommandResult(b"", b"")

    monkeypatch.setattr(
        "tools.local_release_preflight_gates.verify_wheel",
        lambda candidate, **_: __import__("hashlib")
        .sha256(candidate.read_bytes())
        .hexdigest(),
    )
    monkeypatch.setattr(
        "tools.local_release_preflight_gates._verify_sdist_source_payloads",
        lambda *_: 3,
    )
    monkeypatch.setattr(
        "tools.local_release_preflight_gates._verify_sdist_generated_metadata",
        lambda *_: "a" * 64,
    )
    context = LocalGateContext(
        tmp_path,
        environment={"SOURCE_DATE_EPOCH": "1788220800"},
        command_runner=command_runner,
    )
    context.wheel = wheel
    context.sdist = archive_path
    context.sdist_manifest = manifest
    context.sdist_root = "liquent-0.0.1"
    context.sdist_source_file_count = 3
    context.sdist_generated_metadata_sha256 = "a" * 64
    context.wheel_sha256 = __import__("hashlib").sha256(wheel.read_bytes()).hexdigest()
    context.sdist_sha256 = __import__("hashlib").sha256(archive_path.read_bytes()).hexdigest()
    context.bound_source_commit = "a" * 40
    context.bound_source_date_epoch = 1788220800
    context.build_runtime_sha256 = "c" * 64
    context.test_counts = {"normal": 10, "postgres": 2}
    context.postgres_version = "16.10"
    context.quality_evidence_sha256 = _sha256(
        _canonical(_quality_evidence_facts(context))
    )
    identity = _distribution_pair_identity(
        wheel,
        archive_path,
        source_commit=context.bound_source_commit,
        source_date_epoch=context.bound_source_date_epoch,
        build_runtime_sha256=context.build_runtime_sha256,
        quality_evidence_sha256=context.quality_evidence_sha256,
    )
    context.distribution_version = identity["version"]
    context.distribution_pair_sha256 = identity["pair_sha256"]
    context.distribution_directory_identity = _private_output_directory_identity(
        tmp_path
    )

    facts = SdistGate(context).measure(tmp_path)
    assert facts["files"] == 3
    assert facts["roundtrip_wheel_sha256"]

    _write_sdist(archive_path, tmp_path / "replacement", mtime=200, value=2)
    _normalize_sdist(archive_path, "1788220800")

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        SdistGate(context).measure(tmp_path)


@pytest.mark.parametrize("target", ["wheel", "sdist"])
def test_distribution_pair_rejects_later_artifact_replacement(
    tmp_path: Path, target: str
) -> None:
    wheel = tmp_path / "liquent-0.0.1-py3-none-any.whl"
    sdist = tmp_path / "liquent-0.0.1.tar.gz"
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")
    context = LocalGateContext(tmp_path, environment={})
    context.wheel = wheel
    context.sdist = sdist
    context.bound_source_commit = "a" * 40
    context.bound_source_date_epoch = 1788220800
    context.build_runtime_sha256 = "c" * 64
    context.test_counts = {"normal": 10, "postgres": 2}
    context.postgres_version = "16.10"
    context.quality_evidence_sha256 = _sha256(
        _canonical(_quality_evidence_facts(context))
    )
    identity = _distribution_pair_identity(
        wheel,
        sdist,
        source_commit=context.bound_source_commit,
        source_date_epoch=context.bound_source_date_epoch,
        build_runtime_sha256=context.build_runtime_sha256,
        quality_evidence_sha256=context.quality_evidence_sha256,
    )
    context.wheel_sha256 = identity["wheel_sha256"]
    context.sdist_sha256 = identity["sdist_sha256"]
    context.distribution_version = identity["version"]
    context.distribution_pair_sha256 = identity["pair_sha256"]
    context.distribution_directory_identity = _private_output_directory_identity(
        tmp_path
    )
    assert _verify_distribution_pair(context) == (wheel, sdist)

    (wheel if target == "wheel" else sdist).write_bytes(b"replacement")

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _verify_distribution_pair(context)


@pytest.mark.parametrize(
    ("wheel_name", "sdist_name"),
    [
        ("liquent-0.0.1-py3-none-any.whl", "liquent-0.0.2.tar.gz"),
        ("other-0.0.1-py3-none-any.whl", "liquent-0.0.1.tar.gz"),
    ],
)
def test_distribution_pair_identity_rejects_name_or_version_mismatch(
    tmp_path: Path, wheel_name: str, sdist_name: str
) -> None:
    wheel = tmp_path / wheel_name
    sdist = tmp_path / sdist_name
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _distribution_pair_identity(
            wheel,
            sdist,
            source_commit="a" * 40,
            source_date_epoch=1788220800,
            build_runtime_sha256="c" * 64,
            quality_evidence_sha256="e" * 64,
        )


@pytest.mark.parametrize(
    ("source_commit", "source_date_epoch"),
    [("b" * 40, 1788220800), ("a" * 40, 1788220801)],
)
def test_distribution_pair_digest_changes_with_source_identity(
    tmp_path: Path, source_commit: str, source_date_epoch: int
) -> None:
    wheel = tmp_path / "liquent-0.0.1-py3-none-any.whl"
    sdist = tmp_path / "liquent-0.0.1.tar.gz"
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")
    baseline = _distribution_pair_identity(
        wheel,
        sdist,
        source_commit="a" * 40,
        source_date_epoch=1788220800,
        build_runtime_sha256="c" * 64,
        quality_evidence_sha256="e" * 64,
    )
    changed = _distribution_pair_identity(
        wheel,
        sdist,
        source_commit=source_commit,
        source_date_epoch=source_date_epoch,
        build_runtime_sha256="c" * 64,
        quality_evidence_sha256="e" * 64,
    )

    assert changed["pair_sha256"] != baseline["pair_sha256"]


def test_distribution_pair_digest_changes_with_build_runtime(tmp_path: Path) -> None:
    wheel = tmp_path / "liquent-0.0.1-py3-none-any.whl"
    sdist = tmp_path / "liquent-0.0.1.tar.gz"
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")
    baseline = _distribution_pair_identity(
        wheel,
        sdist,
        source_commit="a" * 40,
        source_date_epoch=1788220800,
        build_runtime_sha256="c" * 64,
        quality_evidence_sha256="e" * 64,
    )
    changed = _distribution_pair_identity(
        wheel,
        sdist,
        source_commit="a" * 40,
        source_date_epoch=1788220800,
        build_runtime_sha256="d" * 64,
        quality_evidence_sha256="e" * 64,
    )

    assert changed["pair_sha256"] != baseline["pair_sha256"]


def test_distribution_pair_digest_changes_with_quality_evidence(tmp_path: Path) -> None:
    wheel = tmp_path / "liquent-0.0.1-py3-none-any.whl"
    sdist = tmp_path / "liquent-0.0.1.tar.gz"
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")
    common = {
        "source_commit": "a" * 40,
        "source_date_epoch": 1788220800,
        "build_runtime_sha256": "c" * 64,
    }
    baseline = _distribution_pair_identity(
        wheel, sdist, **common, quality_evidence_sha256="e" * 64
    )
    changed = _distribution_pair_identity(
        wheel, sdist, **common, quality_evidence_sha256="f" * 64
    )

    assert changed["pair_sha256"] != baseline["pair_sha256"]


def _write_source_bound_sdist(
    source_root: Path, archive_path: Path, *, additional: str | None = None
) -> None:
    files = {
        "README.md": b"readme\n",
        "pyproject.toml": b"[project]\nname='liquent'\n",
        "src/liquent/__init__.py": b"",
        "src/liquent_platform/__init__.py": b"",
        "tests/test_example.py": b"def test_example(): pass\n",
    }
    for name, payload in files.items():
        target = source_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    archive_files = {**files, **{name: b"generated\n" for name in GENERATED_SDIST_FILES}}
    if additional is not None:
        archive_files[additional] = b"unreviewed\n"
    root = "liquent-0.0.1"
    with tarfile.open(archive_path, "w:gz") as archive:
        directories = {root}
        for name in archive_files:
            parts = name.split("/")[:-1]
            for index in range(1, len(parts) + 1):
                directories.add(root + "/" + "/".join(parts[:index]))
        for name in sorted(directories):
            member = tarfile.TarInfo(name)
            member.type = tarfile.DIRTYPE
            member.mode = 0o755
            archive.addfile(member)
        for name, payload in sorted(archive_files.items()):
            member = tarfile.TarInfo(f"{root}/{name}")
            member.mode = 0o644
            member.size = len(payload)
            archive.addfile(member, __import__("io").BytesIO(payload))
    _normalize_sdist(archive_path, "1788220800")


def test_sdist_source_gate_accepts_exact_repository_payload_set(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    archive = tmp_path / "liquent-0.0.1.tar.gz"
    _write_source_bound_sdist(source_root, archive)
    assert _verify_sdist_source_payloads(archive, source_root, "liquent-0.0.1") == 5


@pytest.mark.parametrize("mutation", ["changed", "missing", "additional"])
def test_sdist_source_gate_rejects_source_or_archive_drift(
    tmp_path: Path, mutation: str
) -> None:
    source_root = tmp_path / "source"
    archive = tmp_path / "liquent-0.0.1.tar.gz"
    _write_source_bound_sdist(
        source_root,
        archive,
        additional="tools/unreviewed.py" if mutation == "additional" else None,
    )
    candidate = source_root / "src/liquent/__init__.py"
    if mutation == "changed":
        candidate.write_bytes(b"changed")
    elif mutation == "missing":
        candidate.unlink()
    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _verify_sdist_source_payloads(archive, source_root, "liquent-0.0.1")


def _generated_payload_fixture() -> tuple[dict[str, bytes], dict[str, bytes], set[str]]:
    metadata = b"Metadata-Version: 2.4\nName: liquent\n\n"
    entries = b"[console_scripts]\nliquent-test = liquent_platform.test:main\n"
    top_level = b"liquent\nliquent_platform\n"
    archive_names = {*GENERATED_SDIST_FILES, "README.md"}
    sources = "\n".join(
        sorted(archive_names - {"PKG-INFO", "setup.cfg"})
    ).encode()
    payloads = {
        "PKG-INFO": metadata,
        "setup.cfg": EXPECTED_SDIST_SETUP_CFG,
        "liquent.egg-info/PKG-INFO": metadata,
        "liquent.egg-info/SOURCES.txt": sources,
        "liquent.egg-info/dependency_links.txt": b"\n",
        "liquent.egg-info/entry_points.txt": entries,
        "liquent.egg-info/requires.txt": EXPECTED_SDIST_REQUIRES,
        "liquent.egg-info/top_level.txt": top_level,
    }
    wheel_payloads = {
        "METADATA": metadata,
        "entry_points.txt": entries,
        "top_level.txt": top_level,
    }
    return payloads, wheel_payloads, archive_names


def test_generated_sdist_metadata_gate_accepts_consistent_redundant_facts() -> None:
    payloads, wheel_payloads, archive_names = _generated_payload_fixture()
    assert len(
        _validate_sdist_generated_payloads(payloads, wheel_payloads, archive_names)
    ) == 64


@pytest.mark.parametrize(
    ("target", "name"),
    [
        ("payload", "PKG-INFO"),
        ("payload", "liquent.egg-info/entry_points.txt"),
        ("payload", "liquent.egg-info/requires.txt"),
        ("payload", "setup.cfg"),
        ("wheel", "top_level.txt"),
    ],
)
def test_generated_sdist_metadata_gate_rejects_redundant_fact_drift(
    target: str, name: str
) -> None:
    payloads, wheel_payloads, archive_names = _generated_payload_fixture()
    (payloads if target == "payload" else wheel_payloads)[name] = b"changed\n"
    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _validate_sdist_generated_payloads(payloads, wheel_payloads, archive_names)
