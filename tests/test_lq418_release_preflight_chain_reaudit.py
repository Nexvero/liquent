from pathlib import Path

from tools import local_release_preflight_gates as local_gates
from tools.controlled_release_preflight import PHASES
from tools.local_release_preflight_gates import (
    LocalGateContext,
    LocalGateRejected,
    MAX_RELEASE_CANDIDATE_DESCRIPTOR_BYTES,
    MAX_VERIFICATION_EVIDENCE_BYTES,
    _create_private_candidate_output,
    _create_private_workspace_directory,
    _release_candidate_identity,
    _seal_local_bundle,
    _private_output_directory_identity,
    _verify_release_candidate_descriptor,
    _verify_candidate_output_inventory,
    _verify_distribution_artifact_inventory,
    _verify_roundtrip_artifact_inventory,
    _measure_private_installed_tree,
    _installed_distribution_identity,
    _verify_verification_evidence_file,
    _write_new_atomic,
)

import pytest


ROOT = Path(__file__).parents[1]
GATES = ROOT / "tools/local_release_preflight_gates.py"


def test_final_diff_precedes_bundle_in_the_only_phase_order() -> None:
    assert PHASES[-2:] == ("final_diff", "bundle")
    source = GATES.read_text(encoding="utf-8")
    composition = source[source.index("def local_gate_adapters") :]
    assert composition.index("FinalDiffGate(context)") < composition.index(
        "BundleGate(context)"
    )


def test_bundle_requires_measured_final_diff_before_writing_evidence() -> None:
    source = GATES.read_text(encoding="utf-8")
    bundle = source[source.index("class BundleGate") : source.index("class FinalDiffGate")]
    evidence = source[
        source.index("def _verification_evidence_payload") : source.index("class FinalDiffGate")
    ]
    assert "or not self.context.final_diff_verified" in bundle
    assert '"diff_check": "passed"' in evidence
    final = source[source.index("class FinalDiffGate") :]
    assert 'self.context.command(("git", "diff", "--check"))' in final
    assert "self.context.final_diff_verified = True" in final


def test_postgresql_version_is_measured_and_not_synthetic() -> None:
    source = GATES.read_text(encoding="utf-8")
    postgres = source[
        source.index("class PostgresTestsGate") : source.index("class DistributionsGate")
    ]
    bundle = source[source.index("class BundleGate") : source.index("class FinalDiffGate")]
    evidence = source[
        source.index("def _verification_evidence_payload") : source.index("class FinalDiffGate")
    ]
    assert "SHOW server_version" in postgres
    assert "LIQUENT_TEST_DATABASE_URL" in postgres
    assert "self.context.postgres_version = version" in postgres
    assert '"postgresql": context.postgres_version' in evidence
    assert "verified by postgres integration gate" not in source


def test_bundle_scan_and_verification_remain_inside_the_terminal_gate() -> None:
    source = GATES.read_text(encoding="utf-8")
    bundle = source[source.index("class BundleGate") : source.index("class FinalDiffGate")]
    assert bundle.index("build_bundle(") < bundle.index("verify_bundle(bundle)")
    assert 'verified.get("integrity") != "verified"' in bundle
    assert 'verified.get("promotable") is not False' in bundle


def test_release_candidate_identity_binds_pair_evidence_and_bundle(tmp_path: Path) -> None:
    evidence = tmp_path / "verification.json"
    bundle = tmp_path / "liquent-release.tar.gz"
    evidence.write_bytes(b"evidence")
    bundle.write_bytes(b"bundle")
    evidence.chmod(0o600)
    bundle.chmod(0o600)
    context = LocalGateContext(tmp_path, environment={})
    context.verification = evidence
    context.verification_sha256 = __import__("hashlib").sha256(b"evidence").hexdigest()
    context.distribution_pair_sha256 = "a" * 64
    context.bound_source_commit = "b" * 40
    context.distribution_version = "0.0.1"

    identity = _release_candidate_identity(context, bundle=bundle)

    assert identity["schema_version"] == 1
    assert identity["bundle_name"] == bundle.name
    assert identity["bundle_size"] == len(b"bundle")
    assert identity["verification_name"] == evidence.name
    assert identity["verification_size"] == len(b"evidence")
    assert len(identity["release_candidate_sha256"]) == 64
    evidence.write_bytes(b"replacement")
    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _release_candidate_identity(context, bundle=bundle)


@pytest.mark.parametrize("component", ["bundle", "pair", "evidence"])
def test_release_candidate_digest_changes_with_each_bound_component(
    tmp_path: Path, component: str
) -> None:
    evidence = tmp_path / "verification.json"
    bundle = tmp_path / "liquent-release.tar.gz"
    evidence.write_bytes(b"evidence")
    bundle.write_bytes(b"bundle")
    evidence.chmod(0o600)
    bundle.chmod(0o600)
    context = LocalGateContext(tmp_path, environment={})
    context.verification = evidence
    context.verification_sha256 = __import__("hashlib").sha256(b"evidence").hexdigest()
    context.distribution_pair_sha256 = "a" * 64
    context.bound_source_commit = "b" * 40
    context.distribution_version = "0.0.1"
    baseline = _release_candidate_identity(context, bundle=bundle)
    if component == "bundle":
        bundle.write_bytes(b"changed bundle")
    elif component == "pair":
        context.distribution_pair_sha256 = "c" * 64
    else:
        evidence.write_bytes(b"changed evidence")
        context.verification_sha256 = __import__("hashlib").sha256(
            b"changed evidence"
        ).hexdigest()

    changed = _release_candidate_identity(context, bundle=bundle)

    assert changed["release_candidate_sha256"] != baseline["release_candidate_sha256"]


@pytest.mark.parametrize(
    ("artifact", "mutation"),
    [("bundle", "symlink"), ("bundle", "hardlink"), ("evidence", "symlink"), ("evidence", "hardlink")],
)
def test_release_candidate_identity_rejects_artifact_link_drift(
    tmp_path: Path, artifact: str, mutation: str
) -> None:
    evidence = tmp_path / "verification.json"
    bundle = tmp_path / "liquent-release.tar.gz"
    evidence.write_bytes(b"evidence")
    bundle.write_bytes(b"bundle")
    evidence.chmod(0o600)
    bundle.chmod(0o600)
    context = LocalGateContext(tmp_path, environment={})
    context.verification = evidence
    context.verification_sha256 = __import__("hashlib").sha256(b"evidence").hexdigest()
    context.distribution_pair_sha256 = "a" * 64
    context.bound_source_commit = "b" * 40
    context.distribution_version = "0.0.1"
    target = bundle if artifact == "bundle" else evidence
    if mutation == "symlink":
        payload = target.read_bytes()
        outside = tmp_path.parent / f"{artifact}-outside"
        outside.write_bytes(payload)
        outside.chmod(0o600)
        target.unlink()
        target.symlink_to(outside)
    else:
        (tmp_path.parent / f"{artifact}-second-name").hardlink_to(target)

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _release_candidate_identity(context, bundle=bundle)


def test_release_candidate_identity_uses_bound_artifact_descriptors() -> None:
    source = GATES.read_text(encoding="utf-8")
    identity = source[
        source.index("def _read_bound_candidate_artifact") : source.index(
            "def _write_new_atomic"
        )
    ]

    assert "os.O_DIRECTORY | os.O_NOFOLLOW" in identity
    assert "dir_fd=directory_descriptor" in identity
    assert ".read_bytes()" not in identity
    assert ".stat()" not in identity


def test_candidate_descriptor_bytes_equal_hashed_candidate_facts(tmp_path: Path) -> None:
    evidence = tmp_path / "verification.json"
    bundle = tmp_path / "liquent-release.tar.gz"
    descriptor = tmp_path / "release-candidate.json"
    evidence.write_bytes(b"evidence")
    bundle.write_bytes(b"bundle")
    evidence.chmod(0o600)
    bundle.chmod(0o600)
    context = LocalGateContext(tmp_path, environment={})
    context.verification = evidence
    context.verification_sha256 = __import__("hashlib").sha256(b"evidence").hexdigest()
    context.distribution_pair_sha256 = "a" * 64
    context.bound_source_commit = "b" * 40
    context.distribution_version = "0.0.1"
    identity = _release_candidate_identity(context, bundle=bundle)
    facts = {key: value for key, value in identity.items() if key != "release_candidate_sha256"}

    _write_new_atomic(descriptor, __import__("json").dumps(facts, sort_keys=True, separators=(",", ":")).encode() + b"\n")
    _verify_release_candidate_descriptor(descriptor, identity)

    assert __import__("hashlib").sha256(descriptor.read_bytes()).hexdigest() == identity[
        "release_candidate_sha256"
    ]
    assert descriptor.stat().st_mode & 0o777 == 0o600
    assert descriptor.stat().st_nlink == 1
    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _write_new_atomic(descriptor, b"replacement")


def test_candidate_descriptor_rejects_mode_drift(tmp_path: Path) -> None:
    evidence = tmp_path / "verification.json"
    bundle = tmp_path / "liquent-release.tar.gz"
    descriptor = tmp_path / "release-candidate.json"
    evidence.write_bytes(b"evidence")
    bundle.write_bytes(b"bundle")
    evidence.chmod(0o600)
    bundle.chmod(0o600)
    context = LocalGateContext(tmp_path, environment={})
    context.verification = evidence
    context.verification_sha256 = __import__("hashlib").sha256(b"evidence").hexdigest()
    context.distribution_pair_sha256 = "a" * 64
    context.bound_source_commit = "b" * 40
    context.distribution_version = "0.0.1"
    identity = _release_candidate_identity(context, bundle=bundle)
    facts = {key: value for key, value in identity.items() if key != "release_candidate_sha256"}
    payload = __import__("json").dumps(facts, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    _write_new_atomic(descriptor, payload)
    descriptor.chmod(0o644)

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _verify_release_candidate_descriptor(descriptor, identity)


@pytest.mark.parametrize("mutation", ["symlink", "hardlink"])
def test_candidate_descriptor_rejects_link_drift(
    tmp_path: Path, mutation: str
) -> None:
    evidence = tmp_path / "verification.json"
    bundle = tmp_path / "liquent-release.tar.gz"
    descriptor = tmp_path / "release-candidate.json"
    evidence.write_bytes(b"evidence")
    bundle.write_bytes(b"bundle")
    evidence.chmod(0o600)
    bundle.chmod(0o600)
    context = LocalGateContext(tmp_path, environment={})
    context.verification = evidence
    context.verification_sha256 = __import__("hashlib").sha256(b"evidence").hexdigest()
    context.distribution_pair_sha256 = "a" * 64
    context.bound_source_commit = "b" * 40
    context.distribution_version = "0.0.1"
    identity = _release_candidate_identity(context, bundle=bundle)
    facts = {key: value for key, value in identity.items() if key != "release_candidate_sha256"}
    payload = __import__("json").dumps(facts, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    _write_new_atomic(descriptor, payload)
    if mutation == "symlink":
        descriptor.unlink()
        descriptor.symlink_to(evidence)
    else:
        (tmp_path / "second-name").hardlink_to(descriptor)

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _verify_release_candidate_descriptor(descriptor, identity)


def test_candidate_descriptor_verification_uses_bound_descriptors() -> None:
    source = GATES.read_text(encoding="utf-8")
    verification = source[
        source.index("def _verify_release_candidate_descriptor") : source.index(
            "def _verify_verification_evidence_file"
        )
    ]

    assert "os.O_DIRECTORY | os.O_NOFOLLOW" in verification
    assert "dir_fd=directory_descriptor" in verification
    assert "path.read_bytes()" not in verification


@pytest.mark.parametrize("payload", [b"", b"x" * (MAX_RELEASE_CANDIDATE_DESCRIPTOR_BYTES + 1)])
def test_candidate_descriptor_writer_rejects_invalid_size(
    tmp_path: Path, payload: bytes
) -> None:
    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _write_new_atomic(tmp_path / "release-candidate.json", payload)
    assert not (tmp_path / "release-candidate.json").exists()


def test_candidate_descriptor_writer_rolls_back_failed_directory_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tools import local_release_preflight_gates as gates

    real_fsync = gates.os.fsync
    calls = 0

    def fail_directory_sync(descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("directory sync failed")
        real_fsync(descriptor)

    monkeypatch.setattr(gates.os, "fsync", fail_directory_sync)
    target = tmp_path / "release-candidate.json"

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _write_new_atomic(target, b"candidate\n")

    assert not target.exists()
    assert list(tmp_path.iterdir()) == []


def test_candidate_descriptor_rejects_symlinked_output_directory(tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    actual.mkdir(mode=0o700)
    linked = tmp_path / "linked"
    linked.symlink_to(actual, target_is_directory=True)

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _write_new_atomic(linked / "release-candidate.json", b"candidate\n")

    assert list(actual.iterdir()) == []


def test_atomic_candidate_writer_uses_only_bound_directory_operations() -> None:
    source = GATES.read_text(encoding="utf-8")
    writer = source[
        source.index("def _write_new_atomic") : source.index(
            "def _private_output_directory_identity"
        )
    ]

    assert "os.O_DIRECTORY | os.O_NOFOLLOW" in writer
    assert "src_dir_fd=directory" in writer
    assert "dst_dir_fd=directory" in writer
    assert "dir_fd=directory" in writer
    assert "NamedTemporaryFile" not in writer
    assert "path.exists()" not in writer


def test_private_output_directory_rejects_permission_drift(tmp_path: Path) -> None:
    output = tmp_path / "bundle"
    output.mkdir(mode=0o700)
    assert _private_output_directory_identity(output) == (
        output.stat().st_dev,
        output.stat().st_ino,
    )
    output.chmod(0o755)

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _private_output_directory_identity(output)


def test_private_output_directory_identity_rejects_symbolic_link(tmp_path: Path) -> None:
    output = tmp_path / "bundle"
    output.mkdir(mode=0o700)
    linked = tmp_path / "linked"
    linked.symlink_to(output, target_is_directory=True)

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _private_output_directory_identity(linked)


def test_private_output_directory_identity_uses_no_follow_descriptor() -> None:
    source = GATES.read_text(encoding="utf-8")
    identity = source[
        source.index("def _private_output_directory_identity") : source.index(
            "def _seal_local_bundle"
        )
    ]

    assert "os.O_DIRECTORY | os.O_NOFOLLOW" in identity
    assert "os.fstat(descriptor)" in identity
    assert ".lstat()" not in identity


def test_private_candidate_output_is_created_relative_and_bound(tmp_path: Path) -> None:
    output, identity = _create_private_candidate_output(tmp_path)

    assert output == tmp_path / "bundle"
    assert identity == _private_output_directory_identity(output)
    assert output.stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize("mutation", ["existing", "symlink"])
def test_private_candidate_output_rejects_unsafe_workspace_or_target(
    tmp_path: Path, mutation: str
) -> None:
    workspace = tmp_path
    if mutation == "existing":
        (workspace / "bundle").mkdir(mode=0o700)
    else:
        actual = tmp_path / "actual"
        actual.mkdir(mode=0o700)
        workspace = tmp_path / "linked"
        workspace.symlink_to(actual, target_is_directory=True)

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _create_private_candidate_output(workspace)


def test_private_candidate_output_creation_is_directory_relative() -> None:
    source = GATES.read_text(encoding="utf-8")
    creation = source[
        source.index("def _create_private_workspace_directory") : source.index(
            "def _seal_local_bundle"
        )
    ]

    assert "os.O_DIRECTORY | os.O_NOFOLLOW" in creation
    assert "os.mkdir(name, mode=0o700, dir_fd=workspace_descriptor)" in creation
    assert "os.rmdir(name, dir_fd=workspace_descriptor)" in creation
    assert "output.mkdir(" not in creation


def test_all_fixed_workspace_directories_share_private_creation(tmp_path: Path) -> None:
    for name in ("artifacts", "bundle", "installed-wheel", "sdist-wheel-roundtrip"):
        output, identity = _create_private_workspace_directory(tmp_path, name)
        assert identity == _private_output_directory_identity(output)
        assert output.stat().st_mode & 0o777 == 0o700

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _create_private_workspace_directory(tmp_path, "caller-selected")


def test_local_bundle_seal_binds_private_file_metadata(tmp_path: Path) -> None:
    output = tmp_path / "bundle"
    output.mkdir(mode=0o700)
    bundle = output / "liquent-release.tar.gz"
    bundle.write_bytes(b"bundle")

    digest = _seal_local_bundle(
        bundle, parent_identity=_private_output_directory_identity(output)
    )

    assert digest == __import__("hashlib").sha256(b"bundle").hexdigest()
    assert bundle.stat().st_mode & 0o777 == 0o600
    assert bundle.stat().st_nlink == 1


@pytest.mark.parametrize("mutation", ["symlink", "hardlink", "oversized"])
def test_local_bundle_seal_rejects_unsafe_file_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    output = tmp_path / "bundle"
    output.mkdir(mode=0o700)
    bundle = output / "liquent-release.tar.gz"
    if mutation == "symlink":
        source = tmp_path / "source"
        source.write_bytes(b"bundle")
        bundle.symlink_to(source)
    else:
        bundle.write_bytes(b"bundle")
        if mutation == "hardlink":
            (output / "second-name").hardlink_to(bundle)
        else:
            monkeypatch.setattr(
                "tools.local_release_preflight_gates.MAX_LOCAL_RELEASE_BUNDLE_BYTES",
                1,
            )

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _seal_local_bundle(
            bundle, parent_identity=_private_output_directory_identity(output)
        )


def test_local_bundle_seal_uses_bound_directory_relative_open() -> None:
    source = GATES.read_text(encoding="utf-8")
    sealing = source[
        source.index("def _seal_local_bundle") : source.index(
            "def _verify_release_candidate_descriptor"
        )
    ]

    assert "os.O_DIRECTORY | os.O_NOFOLLOW" in sealing
    assert "dir_fd=directory_descriptor" in sealing
    assert "os.open(path," not in sealing


def test_verification_evidence_file_is_private_atomic_and_bound(tmp_path: Path) -> None:
    output = tmp_path / "bundle"
    output.mkdir(mode=0o700)
    identity = _private_output_directory_identity(output)
    evidence = output / "verification.json"
    payload = b'{"schema_version":1}\n'
    digest = __import__("hashlib").sha256(payload).hexdigest()

    _write_new_atomic(evidence, payload, max_bytes=MAX_VERIFICATION_EVIDENCE_BYTES)
    _verify_verification_evidence_file(
        evidence,
        expected_payload=payload,
        expected_sha256=digest,
        parent_identity=identity,
    )

    assert evidence.stat().st_mode & 0o777 == 0o600
    assert evidence.stat().st_nlink == 1


@pytest.mark.parametrize("mutation", ["mode", "bytes", "hardlink", "symlink"])
def test_verification_evidence_file_rejects_metadata_or_byte_drift(
    tmp_path: Path, mutation: str
) -> None:
    output = tmp_path / "bundle"
    output.mkdir(mode=0o700)
    identity = _private_output_directory_identity(output)
    evidence = output / "verification.json"
    payload = b'{"schema_version":1}\n'
    digest = __import__("hashlib").sha256(payload).hexdigest()
    _write_new_atomic(evidence, payload, max_bytes=MAX_VERIFICATION_EVIDENCE_BYTES)
    if mutation == "mode":
        evidence.chmod(0o644)
    elif mutation == "bytes":
        evidence.write_bytes(b"changed\n")
        evidence.chmod(0o600)
    elif mutation == "hardlink":
        (output / "second-name").hardlink_to(evidence)
    else:
        evidence.unlink()
        evidence.symlink_to(tmp_path / "outside")

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _verify_verification_evidence_file(
            evidence,
            expected_payload=payload,
            expected_sha256=digest,
            parent_identity=identity,
        )


def test_verification_evidence_check_uses_bound_descriptors() -> None:
    source = GATES.read_text(encoding="utf-8")
    verification = source[
        source.index("def _verify_verification_evidence_file") : source.index(
            "def _verify_candidate_output_inventory"
        )
    ]

    assert "os.O_DIRECTORY | os.O_NOFOLLOW" in verification
    assert "dir_fd=directory_descriptor" in verification
    assert "path.read_bytes()" not in verification


def test_candidate_output_inventory_binds_exact_three_files(tmp_path: Path) -> None:
    output = tmp_path / "bundle"
    output.mkdir(mode=0o700)
    payloads = {
        "liquent-release.tar.gz": b"bundle",
        "release-candidate.json": b"candidate",
        "verification.json": b"verification",
    }
    for name, payload in payloads.items():
        (output / name).write_bytes(payload)
        (output / name).chmod(0o600)
    digests = {
        name: __import__("hashlib").sha256(payload).hexdigest()
        for name, payload in payloads.items()
    }

    sizes = {name: len(payload) for name, payload in payloads.items()}
    first = _verify_candidate_output_inventory(
        output, expected_digests=digests, expected_sizes=sizes
    )
    second = _verify_candidate_output_inventory(
        output, expected_digests=digests, expected_sizes=sizes
    )

    assert first == second
    assert len(first) == 64


@pytest.mark.parametrize("mutation", ["extra", "missing", "symlink"])
def test_candidate_output_inventory_rejects_topology_drift(
    tmp_path: Path, mutation: str
) -> None:
    output = tmp_path / "bundle"
    output.mkdir(mode=0o700)
    payloads = {"bundle": b"b", "candidate": b"c", "verification": b"v"}
    for name, payload in payloads.items():
        (output / name).write_bytes(payload)
        (output / name).chmod(0o600)
    digests = {
        name: __import__("hashlib").sha256(payload).hexdigest()
        for name, payload in payloads.items()
    }
    sizes = {name: len(payload) for name, payload in payloads.items()}
    if mutation == "extra":
        (output / "extra").write_bytes(b"x")
    elif mutation == "missing":
        (output / "candidate").unlink()
    else:
        (output / "candidate").unlink()
        (output / "candidate").symlink_to(output / "bundle")

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _verify_candidate_output_inventory(
            output, expected_digests=digests, expected_sizes=sizes
        )


@pytest.mark.parametrize("mutation", ["mode", "hardlink"])
def test_candidate_output_inventory_rejects_file_metadata_drift(
    tmp_path: Path, mutation: str
) -> None:
    output = tmp_path / "bundle"
    output.mkdir(mode=0o700)
    payloads = {"bundle": b"b", "candidate": b"c", "verification": b"v"}
    for name, payload in payloads.items():
        (output / name).write_bytes(payload)
        (output / name).chmod(0o600)
    digests = {
        name: __import__("hashlib").sha256(payload).hexdigest()
        for name, payload in payloads.items()
    }
    sizes = {name: len(payload) for name, payload in payloads.items()}
    if mutation == "mode":
        (output / "candidate").chmod(0o644)
    else:
        outside = tmp_path / "outside"
        outside.hardlink_to(output / "candidate")

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _verify_candidate_output_inventory(
            output, expected_digests=digests, expected_sizes=sizes
        )


def test_candidate_output_inventory_rejects_expected_size_drift(
    tmp_path: Path,
) -> None:
    output = tmp_path / "bundle"
    output.mkdir(mode=0o700)
    payloads = {"bundle": b"b", "candidate": b"c", "verification": b"v"}
    for name, payload in payloads.items():
        (output / name).write_bytes(payload)
        (output / name).chmod(0o600)
    digests = {
        name: __import__("hashlib").sha256(payload).hexdigest()
        for name, payload in payloads.items()
    }
    sizes = {name: len(payload) for name, payload in payloads.items()}
    sizes["candidate"] += 1

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _verify_candidate_output_inventory(
            output, expected_digests=digests, expected_sizes=sizes
        )


def test_candidate_output_inventory_uses_directory_relative_file_opens() -> None:
    source = GATES.read_text(encoding="utf-8")
    inventory = source[
        source.index("def _verify_candidate_output_inventory") : source.index(
            "class BundleGate"
        )
    ]

    assert "os.O_DIRECTORY | os.O_NOFOLLOW" in inventory
    assert "dir_fd=directory_descriptor" in inventory
    assert "path.read_bytes()" not in inventory
    assert inventory.index("before.st_size != expected_sizes[name]") < inventory.index(
        "while chunk := os.read"
    )


def test_distribution_artifact_inventory_binds_exact_pair(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(mode=0o700)
    payloads = {"liquent-1.whl": b"wheel", "liquent-1.tar.gz": b"sdist"}
    for name, payload in payloads.items():
        (artifacts / name).write_bytes(payload)
        (artifacts / name).chmod(0o600)
    digests = {
        name: __import__("hashlib").sha256(payload).hexdigest()
        for name, payload in payloads.items()
    }

    first = _verify_distribution_artifact_inventory(
        artifacts, expected_digests=digests
    )
    second = _verify_distribution_artifact_inventory(
        artifacts, expected_digests=digests
    )

    assert first == second
    assert len(first) == 64


@pytest.mark.parametrize("mutation", ["extra", "missing", "symlink", "hardlink", "mode"])
def test_distribution_artifact_inventory_rejects_drift(
    tmp_path: Path, mutation: str
) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(mode=0o700)
    payloads = {"wheel": b"w", "sdist": b"s"}
    for name, payload in payloads.items():
        (artifacts / name).write_bytes(payload)
        (artifacts / name).chmod(0o600)
    digests = {
        name: __import__("hashlib").sha256(payload).hexdigest()
        for name, payload in payloads.items()
    }
    if mutation == "extra":
        (artifacts / "extra").write_bytes(b"x")
    elif mutation == "missing":
        (artifacts / "wheel").unlink()
    elif mutation == "symlink":
        (artifacts / "wheel").unlink()
        (artifacts / "wheel").symlink_to(artifacts / "sdist")
    elif mutation == "hardlink":
        (tmp_path / "second-name").hardlink_to(artifacts / "wheel")
    else:
        (artifacts / "wheel").chmod(0o644)

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _verify_distribution_artifact_inventory(
            artifacts, expected_digests=digests
        )


def test_roundtrip_artifact_inventory_binds_exact_wheel(tmp_path: Path) -> None:
    roundtrip = tmp_path / "sdist-wheel-roundtrip"
    roundtrip.mkdir(mode=0o700)
    wheel = roundtrip / "liquent-1.whl"
    wheel.write_bytes(b"wheel")
    wheel.chmod(0o600)
    digest = __import__("hashlib").sha256(b"wheel").hexdigest()

    first = _verify_roundtrip_artifact_inventory(
        roundtrip, expected_digests={wheel.name: digest}
    )
    second = _verify_roundtrip_artifact_inventory(
        roundtrip, expected_digests={wheel.name: digest}
    )

    assert first == second
    assert len(first) == 64


@pytest.mark.parametrize("mutation", ["extra", "symlink", "mode"])
def test_roundtrip_artifact_inventory_rejects_drift(
    tmp_path: Path, mutation: str
) -> None:
    roundtrip = tmp_path / "sdist-wheel-roundtrip"
    roundtrip.mkdir(mode=0o700)
    wheel = roundtrip / "liquent-1.whl"
    wheel.write_bytes(b"wheel")
    wheel.chmod(0o600)
    digest = __import__("hashlib").sha256(b"wheel").hexdigest()
    if mutation == "extra":
        (roundtrip / "extra").write_bytes(b"x")
    elif mutation == "symlink":
        wheel.unlink()
        wheel.symlink_to(tmp_path / "outside")
    else:
        wheel.chmod(0o644)

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _verify_roundtrip_artifact_inventory(
            roundtrip, expected_digests={wheel.name: digest}
        )


def test_private_installed_tree_normalizes_and_remeasures(tmp_path: Path) -> None:
    root = tmp_path / "installed-wheel"
    root.mkdir(mode=0o700)
    package = root / "liquent"
    package.mkdir(mode=0o755)
    module = package / "__init__.py"
    module.write_bytes(b"VALUE = 1\n")
    marker = package / "py.typed"
    marker.write_bytes(b"")

    first = _measure_private_installed_tree(root, normalize=True)
    second = _measure_private_installed_tree(root, normalize=False)

    assert first == second
    assert root.stat().st_mode & 0o777 == 0o700
    assert package.stat().st_mode & 0o777 == 0o700
    assert module.stat().st_mode & 0o777 == 0o600
    assert marker.stat().st_mode & 0o777 == 0o600
    assert first["files"] == 2


@pytest.mark.parametrize("mutation", ["extra", "symlink", "mode"])
def test_private_installed_tree_rejects_terminal_drift(
    tmp_path: Path, mutation: str
) -> None:
    root = tmp_path / "installed-wheel"
    root.mkdir(mode=0o700)
    package = root / "liquent"
    package.mkdir(mode=0o700)
    module = package / "__init__.py"
    module.write_bytes(b"VALUE = 1\n")
    baseline = _measure_private_installed_tree(root, normalize=True)
    if mutation == "extra":
        extra = package / "extra.py"
        extra.write_bytes(b"x\n")
        extra.chmod(0o600)
    elif mutation == "symlink":
        (package / "linked.py").symlink_to(module)
    else:
        module.chmod(0o644)

    if mutation in {"mode", "symlink"}:
        with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
            _measure_private_installed_tree(root, normalize=False)
    else:
        changed = _measure_private_installed_tree(root, normalize=False)
        assert changed["sha256"] != baseline["sha256"]


def test_installed_distribution_identity_is_canonical_and_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = tmp_path / "liquent.whl"
    wheel.write_bytes(b"wheel")
    entries = [
        {"name": f"liquent-command-{index}", "target": f"package.module{index}:main"}
        for index in reversed(range(71))
    ]
    monkeypatch.setattr(
        local_gates,
        "_wheel_details",
        lambda value: {
            "entry_points": entries,
            "package_name": "liquent",
            "package_version": "1.2.3",
        },
    )

    identity = _installed_distribution_identity(wheel)

    assert identity["schema_version"] == 1
    assert identity["package_name"] == "liquent"
    assert identity["package_version"] == "1.2.3"
    assert [entry["name"] for entry in identity["entry_points"]] == sorted(
        entry["name"] for entry in entries
    )
    assert len(identity["sha256"]) == 64


@pytest.mark.parametrize("mutation", ["name", "version", "target"])
def test_installed_distribution_identity_changes_with_bound_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    wheel = tmp_path / "liquent.whl"
    wheel.write_bytes(b"wheel")
    entries = [
        {"name": f"liquent-command-{index}", "target": f"package.module{index}:main"}
        for index in range(71)
    ]
    details = {
        "entry_points": entries,
        "package_name": "liquent",
        "package_version": "1.2.3",
    }
    monkeypatch.setattr(local_gates, "_wheel_details", lambda value: details)
    baseline = _installed_distribution_identity(wheel)["sha256"]
    if mutation == "name":
        entries[0] = {**entries[0], "name": "liquent-changed"}
    elif mutation == "version":
        details["package_version"] = "1.2.4"
    else:
        entries[0] = {**entries[0], "target": "package.changed:main"}

    assert _installed_distribution_identity(wheel)["sha256"] != baseline


def test_entry_point_gate_binds_exact_installed_distribution() -> None:
    source = GATES.read_text(encoding="utf-8")
    gate = source[source.index("class EntryPointsGate") : source.index("class SdistGate")]
    bundle = source[source.index("class BundleGate") : source.index("class FinalDiffGate")]

    assert "assert len(ds)==1" in gate
    assert "assert all(x.group=='console_scripts' for x in all_entries)" in gate
    assert "assert d.metadata['Name']=='liquent'" in gate
    assert "assert actual==expected" in gate
    assert "assert all(callable(x) for x in loaded)" in gate
    assert "installed_distribution_sha256" in gate
    assert "installed_distribution_sha256" in bundle


def test_entry_point_install_is_configuration_independent() -> None:
    source = GATES.read_text(encoding="utf-8")
    gate = source[source.index("class EntryPointsGate") : source.index("class SdistGate")]

    assert '"pip",\n                "--isolated",' in gate
    assert '"--disable-pip-version-check"' in gate
    assert '"--no-compile"' in gate
    assert '"--no-deps"' in gate
    assert '"--no-index"' in gate
    assert "PYTHONPATH" not in gate


def test_entry_point_loader_is_isolated_and_origin_bound() -> None:
    source = GATES.read_text(encoding="utf-8")
    gate = source[source.index("class EntryPointsGate") : source.index("class SdistGate")]

    assert '(self.context.python_executable, "-I", "-c", script)' in gate
    assert "sys.path.insert(0,str(root))" in gate
    assert "resolve(strict=True)" in gate
    assert "inspect.getmodule(x).__file__" in gate
    assert "is_relative_to(root)" in gate


def test_installed_tree_rejects_bound_root_replacement(tmp_path: Path) -> None:
    root = tmp_path / "installed-wheel"
    root.mkdir(mode=0o700)
    identity = _private_output_directory_identity(root)
    root.rmdir()
    root.mkdir(mode=0o700)
    package = root / "liquent"
    package.mkdir(mode=0o700)
    module = package / "__init__.py"
    module.write_bytes(b"VALUE = 1\n")
    module.chmod(0o600)

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _measure_private_installed_tree(
            root, normalize=False, expected_identity=identity
        )


def test_entry_point_and_bundle_gates_retain_installed_root_identity() -> None:
    source = GATES.read_text(encoding="utf-8")
    gate = source[source.index("class EntryPointsGate") : source.index("class SdistGate")]
    bundle = source[source.index("class BundleGate") : source.index("class FinalDiffGate")]

    install = gate.index("self.context.command(")
    load = gate.index("self.context.command_runner(")
    checks = [
        index
        for index in range(len(gate))
        if gate.startswith("_private_output_directory_identity(target)", index)
    ]
    assert install < checks[0] < load < checks[1]
    assert "expected_identity=target_identity" in gate
    assert "self.context.installed_tree_identity = target_identity" in gate
    assert "if installed_tree_identity is None" in bundle
    assert "expected_identity=installed_tree_identity" in bundle


def test_distribution_inventory_rejects_bound_directory_replacement(
    tmp_path: Path,
) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(mode=0o700)
    identity = _private_output_directory_identity(artifacts)
    artifacts.rmdir()
    artifacts.mkdir(mode=0o700)
    wheel = artifacts / "liquent.whl"
    sdist = artifacts / "liquent.tar.gz"
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")
    wheel.chmod(0o600)
    sdist.chmod(0o600)

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _verify_distribution_artifact_inventory(
            artifacts,
            expected_digests={
                wheel.name: __import__("hashlib").sha256(b"wheel").hexdigest(),
                sdist.name: __import__("hashlib").sha256(b"sdist").hexdigest(),
            },
            expected_directory_identity=identity,
        )


def test_distribution_directory_identity_spans_build_and_terminal_inventory() -> None:
    source = GATES.read_text(encoding="utf-8")
    distributions = source[
        source.index("class DistributionsGate") : source.index("class WheelGate")
    ]
    pair = source[
        source.index("def _verify_distribution_pair") : source.index("class MeasuredGate")
    ]
    bundle = source[source.index("class BundleGate") : source.index("class FinalDiffGate")]

    build = distributions.index("self.context.command(")
    checks = [
        index
        for index in range(len(distributions))
        if distributions.startswith("_private_output_directory_identity(artifacts)", index)
    ]
    assert build < checks[0] < checks[1]
    assert "self.context.distribution_directory_identity = artifacts_identity" in distributions
    assert "context.distribution_directory_identity is None" in pair
    assert "!= context.distribution_directory_identity" in pair
    assert "expected_directory_identity=self.context.distribution_directory_identity" in bundle


def test_roundtrip_inventory_rejects_bound_directory_replacement(tmp_path: Path) -> None:
    roundtrip = tmp_path / "sdist-wheel-roundtrip"
    roundtrip.mkdir(mode=0o700)
    identity = _private_output_directory_identity(roundtrip)
    roundtrip.rmdir()
    roundtrip.mkdir(mode=0o700)
    wheel = roundtrip / "liquent.whl"
    wheel.write_bytes(b"wheel")
    wheel.chmod(0o600)

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _verify_roundtrip_artifact_inventory(
            roundtrip,
            expected_digests={
                wheel.name: __import__("hashlib").sha256(b"wheel").hexdigest()
            },
            expected_directory_identity=identity,
        )


def test_roundtrip_directory_identity_spans_rebuild_and_terminal_inventory() -> None:
    source = GATES.read_text(encoding="utf-8")
    sdist = source[source.index("class SdistGate") : source.index("def _verification_evidence_payload")]
    bundle = source[source.index("class BundleGate") : source.index("class FinalDiffGate")]

    rebuild = sdist.index("self.context.command(")
    checks = [
        index
        for index in range(len(sdist))
        if sdist.startswith("_private_output_directory_identity(roundtrip)", index)
    ]
    assert rebuild < checks[0] < checks[1]
    assert "self.context.roundtrip_directory_identity = roundtrip_identity" in sdist
    assert "self.context.roundtrip_directory_identity is None" in bundle
    assert "expected_directory_identity=self.context.roundtrip_directory_identity" in bundle


def test_reaudit_document_and_roadmap_keep_release_claims_bounded() -> None:
    document = (ROOT / "docs/lq-418-controlled-release-preflight-chain-reaudit.md").read_text(
        encoding="utf-8"
    )
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(
        encoding="utf-8"
    )
    assert "kein echter Packaginglauf" in document
    assert "keine Publication-, Promotion- oder Deploymentfreigabe" in document
    assert "- LQ-418 controlled release preflight chain reaudit:" in roadmap
    assert "nächster Slice LQ-419" in roadmap
