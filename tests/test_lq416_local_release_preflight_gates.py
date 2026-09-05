from pathlib import Path

import pytest

import tools.local_release_preflight_gates as gates

from tools.controlled_release_preflight import PHASES
from tools.local_release_preflight_gates import (
    LOCKED_TOOLS,
    EXPECTED_PYTHON_VERSION,
    EXPECTED_ZLIB_BUILD_VERSION,
    EXPECTED_ZLIB_RUNTIME_VERSION,
    MAX_PROCESS_OUTPUT_BYTES,
    PROCESS_TIMEOUT_SECONDS,
    CommandResult,
    LocalGateContext,
    LocalGateRejected,
    MeasuredGate,
    RuntimeGate,
    _compression_runtime_facts,
    _canonical,
    _quality_evidence_facts,
    _sha256,
    _verification_evidence_payload,
    local_gate_adapters,
)


ROOT = Path(__file__).parents[1]


def test_composition_has_exact_fixed_phase_set_and_order() -> None:
    context = LocalGateContext(ROOT, environment={}, command_runner=lambda *_: CommandResult(b"", b""))
    assert tuple(local_gate_adapters(context)) == PHASES


def test_locked_runtime_versions_match_the_repository_lock() -> None:
    lock = (ROOT / "requirements/ci.lock").read_text(encoding="utf-8")
    assert LOCKED_TOOLS == {
        "build": "1.5.0",
        "pytest": "9.1.1",
        "setuptools": "80.10.2",
        "wheel": "0.47.0",
    }
    assert PROCESS_TIMEOUT_SECONDS == 900.0
    assert MAX_PROCESS_OUTPUT_BYTES == 1_048_576
    assert all(f"{name}=={version}" in lock for name, version in LOCKED_TOOLS.items())
    assert EXPECTED_PYTHON_VERSION == (3, 12, 14)
    assert EXPECTED_ZLIB_BUILD_VERSION == "1.2.12"
    assert EXPECTED_ZLIB_RUNTIME_VERSION == "1.2.12"


def test_runtime_gate_reports_exact_compression_environment() -> None:
    facts = _compression_runtime_facts()

    assert facts["python"] == "3.12.14"
    assert facts["zlib_build"] == "1.2.12"
    assert facts["zlib_runtime"] == "1.2.12"


def test_runtime_gate_captures_canonical_build_runtime_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = LocalGateContext(tmp_path, environment={})
    monkeypatch.setattr(gates.metadata, "version", lambda name: LOCKED_TOOLS[name])

    facts = RuntimeGate(context).measure(tmp_path)

    assert facts["build_runtime_sha256"] == context.build_runtime_sha256
    assert isinstance(context.build_runtime_sha256, str)
    assert len(context.build_runtime_sha256) == 64


def test_quality_evidence_binds_both_test_runs_and_warning_counts(tmp_path: Path) -> None:
    context = LocalGateContext(tmp_path, environment={})
    context.test_counts = {"normal": 7000, "postgres": 120}
    context.warning_count = 3
    context.postgres_warning_count = 1
    context.postgres_version = "16.10"

    facts = _quality_evidence_facts(context)

    assert facts == {
        "normal_command": "python -m pytest -q",
        "normal_passed": 7000,
        "normal_warnings": 3,
        "postgres_command": "python -m pytest -m postgres_integration -q",
        "postgres_passed": 120,
        "postgres_warnings": 1,
        "postgresql": "16.10",
    }


def test_verification_evidence_payload_is_canonical_and_quality_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = LocalGateContext(tmp_path, environment={})
    context.bound_source_commit = "a" * 40
    context.test_counts = {"normal": 7000, "postgres": 120}
    context.postgres_version = "16.10"
    context.final_diff_verified = True
    context.quality_evidence_sha256 = _sha256(
        _canonical(_quality_evidence_facts(context))
    )
    versions = {
        "psycopg": "3.2.9",
        "pytest": "9.1.1",
        "SQLAlchemy": "2.0.43",
    }
    monkeypatch.setattr(gates.metadata, "version", versions.__getitem__)

    first = _verification_evidence_payload(context, commit="a" * 40)
    second = _verification_evidence_payload(context, commit="a" * 40)

    assert first == second
    context.test_counts["normal"] += 1
    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _verification_evidence_payload(context, commit="a" * 40)


@pytest.mark.parametrize(
    ("attribute", "value"),
    [("ZLIB_VERSION", "1.2.11"), ("ZLIB_RUNTIME_VERSION", "1.3.1")],
)
def test_runtime_gate_rejects_zlib_drift(
    monkeypatch: pytest.MonkeyPatch, attribute: str, value: str
) -> None:
    monkeypatch.setattr(gates.zlib, attribute, value)

    with pytest.raises(gates.LocalGateRejected, match="local release preflight gate rejected"):
        _compression_runtime_facts()


def test_every_gate_rechecks_clean_source_commit_before_measurement() -> None:
    source = (ROOT / "tools/local_release_preflight_gates.py").read_text(encoding="utf-8")
    execute = source[source.index("    def execute(self, workspace: Path) -> bytes:") :]
    assert "commit = self.context.source_commit()" in execute
    assert '"status": "passed"' in execute
    assert "facts_sha256" in execute
    assert "self.context.bound_source_commit != commit" in execute
    assert 'self.context.environment.get("SOURCE_DATE_EPOCH")' in execute


class _ProbeGate(MeasuredGate):
    phase = "runtime"

    def measure(self, workspace: Path) -> dict[str, object]:
        return {"measured": True}


def test_gate_chain_rejects_clean_commit_change_between_phases(tmp_path: Path) -> None:
    observed = {"commit": "a" * 40}

    def runner(argv: tuple[str, ...], *_: object) -> CommandResult:
        if "rev-parse" in argv:
            return CommandResult(observed["commit"].encode(), b"")
        return CommandResult(b"", b"")

    context = LocalGateContext(tmp_path, environment={}, command_runner=runner)
    _ProbeGate(context).execute(tmp_path)
    observed["commit"] = "b" * 40

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _ProbeGate(context).execute(tmp_path)


def test_gate_chain_rejects_source_date_epoch_change(tmp_path: Path) -> None:
    def runner(argv: tuple[str, ...], *_: object) -> CommandResult:
        if "rev-parse" in argv:
            return CommandResult(b"a" * 40, b"")
        return CommandResult(b"", b"")

    context = LocalGateContext(
        tmp_path,
        environment={"SOURCE_DATE_EPOCH": "1788220801"},
        command_runner=runner,
    )
    context.bound_source_commit = "a" * 40
    context.bound_source_date_epoch = 1788220800

    with pytest.raises(LocalGateRejected, match="local release preflight gate rejected"):
        _ProbeGate(context).execute(tmp_path)


def test_commands_and_artifact_checks_are_fixed_inside_adapters() -> None:
    source = (ROOT / "tools/local_release_preflight_gates.py").read_text(encoding="utf-8")
    required = (
        '"pytest", "-q"',
        '"postgres_integration"',
        '"build"',
        '"--no-isolation"',
        'expected_member_set_sha256=EXPECTED_WHEEL_MEMBER_SET_SHA256',
        'source_root=self.context.source_root',
        '"pip",\n                "--isolated",\n                "install",',
        '"--no-compile"',
        '"--no-deps"',
        '"--no-index"',
        'build_bundle(',
        'verify_bundle(bundle)',
        '("git", "diff", "--check")',
        "or not self.context.final_diff_verified",
        '"postgresql": context.postgres_version',
    )
    assert all(item in source for item in required)


def test_no_publication_or_deployment_adapter_is_exposed() -> None:
    context = LocalGateContext(ROOT, environment={}, command_runner=lambda *_: CommandResult(b"", b""))
    gates = local_gate_adapters(context)
    assert "publish" not in gates
    assert "promotion" not in gates
    assert "deployment" not in gates
    assert isinstance(gates["runtime"], RuntimeGate)
