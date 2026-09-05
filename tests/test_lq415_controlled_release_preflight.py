from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from tools import controlled_release_preflight as controlled
from tools.controlled_release_preflight import (
    EVIDENCE_NAME,
    MAX_CONTROLLED_EVIDENCE_BYTES,
    MAX_GATE_RECEIPT_BYTES,
    PHASES,
    ControlledPreflightRejected,
    ControlledReleasePreflight,
    GateReceipt,
    PHASE_OUTPUT_DIRECTORIES,
    WORKSPACE_INVENTORY,
    _write_private_workspace_evidence,
    _verify_private_workspace_evidence,
    _verify_private_workspace_inventory,
    _private_output_parent_identity,
    _private_workspace_child_identity,
    _private_workspace_identity,
    _publish_private_workspace,
    _verify_intermediate_workspace_entries,
    _verify_bound_child_directory_identities,
)


def _replace_empty_directory(path: Path, *, mode: int = 0o700) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        path.rmdir()
        path.mkdir(mode=mode)
    finally:
        os.close(descriptor)


def _replace_file(path: Path, payload: bytes, *, mode: int) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        path.unlink()
        path.write_bytes(payload)
        path.chmod(mode)
    finally:
        os.close(descriptor)


COMMIT = "a" * 40


def _receipt(phase: str, *, commit: str = COMMIT) -> bytes:
    return (
        json.dumps(
            {
                "facts_sha256": hashlib.sha256(phase.encode()).hexdigest(),
                "phase": phase,
                "schema_version": 1,
                "source_commit": commit,
                "status": "passed",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("ascii")


class Gate:
    def __init__(self, phase: str, calls: list[str], value: bytes | None = None):
        self.phase = phase
        self.calls = calls
        self.value = value

    def execute(self, workspace: Path) -> bytes:
        assert workspace.is_dir()
        self.calls.append(self.phase)
        created = {
            "distributions": "artifacts",
            "entrypoints": "installed-wheel",
            "sdist": "sdist-wheel-roundtrip",
            "bundle": "bundle",
        }.get(self.phase)
        if created is not None:
            (workspace / created).mkdir(mode=0o700)
        return self.value if self.value is not None else _receipt(self.phase)


def _gates(calls: list[str]) -> dict[str, Gate]:
    return {phase: Gate(phase, calls) for phase in PHASES}


def _rejected(operation) -> None:
    try:
        operation()
    except ControlledPreflightRejected as error:
        assert str(error) == "controlled release preflight rejected"
    else:
        raise AssertionError("expected detail-limited rejection")


def test_success_runs_fixed_order_and_atomically_publishes_evidence(tmp_path: Path) -> None:
    calls: list[str] = []
    output = tmp_path / "result"
    evidence = ControlledReleasePreflight(_gates(calls)).run(output)

    assert calls == list(PHASES)
    assert evidence == output / EVIDENCE_NAME
    document = json.loads(evidence.read_text(encoding="ascii"))
    assert document["outcome"] == "passed"
    assert document["source_commit"] == COMMIT
    assert [item["phase"] for item in document["phases"]] == list(PHASES)
    assert document["publishing_authorized"] is False
    assert document["deployment_authorized"] is False
    assert evidence.stat().st_mode & 0o777 == 0o600
    assert evidence.stat().st_nlink == 1


def test_failure_stops_once_and_leaves_no_output_or_success_evidence(tmp_path: Path) -> None:
    calls: list[str] = []
    gates = _gates(calls)
    gates["postgres_tests"] = Gate("postgres_tests", calls, b"not-json")
    output = tmp_path / "result"

    _rejected(lambda: ControlledReleasePreflight(gates).run(output))

    assert calls == list(PHASES[:4])
    assert not output.exists()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("mutation", ["mode", "identity"])
def test_gate_workspace_drift_fails_before_next_phase(
    tmp_path: Path, mutation: str
) -> None:
    calls: list[str] = []

    class MutatingGate(Gate):
        def execute(self, workspace: Path) -> bytes:
            value = super().execute(workspace)
            if mutation == "mode":
                workspace.chmod(0o755)
            else:
                _replace_empty_directory(workspace)
            return value

    gates = _gates(calls)
    gates["runtime"] = MutatingGate("runtime", calls)

    _rejected(lambda: ControlledReleasePreflight(gates).run(tmp_path / "result"))

    assert calls == ["runtime"]
    assert list(tmp_path.iterdir()) == []


def test_phase_output_directory_replacement_fails_before_later_phase(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    class ReplacingGate(Gate):
        def execute(self, workspace: Path) -> bytes:
            artifacts = workspace / "artifacts"
            _replace_empty_directory(artifacts)
            return super().execute(workspace)

    gates = _gates(calls)
    gates["wheel"] = ReplacingGate("wheel", calls)

    _rejected(lambda: ControlledReleasePreflight(gates).run(tmp_path / "result"))

    assert calls == ["runtime", "source", "normal_tests", "postgres_tests", "distributions", "wheel"]
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("entry_kind", ["future_output", "foreign_file"])
def test_phase_cannot_leave_unexpected_intermediate_workspace_entry(
    tmp_path: Path, entry_kind: str
) -> None:
    calls: list[str] = []

    class PollutingGate(Gate):
        def execute(self, workspace: Path) -> bytes:
            self.calls.append(self.phase)
            if entry_kind == "future_output":
                (workspace / "bundle").mkdir(mode=0o700)
            else:
                (workspace / "foreign").write_bytes(b"data")
            return _receipt(self.phase)

    gates = _gates(calls)
    gates["runtime"] = PollutingGate("runtime", calls)

    _rejected(lambda: ControlledReleasePreflight(gates).run(tmp_path / "result"))

    assert calls == ["runtime"]
    assert list(tmp_path.iterdir()) == []


def test_workspace_identity_checks_surround_every_gate_execution() -> None:
    source = (
        Path(__file__).parents[1] / "tools/controlled_release_preflight.py"
    ).read_text(encoding="utf-8")
    run = source[source.index("    def run(") : source.index("@contextmanager")]
    execute = "raw = self._gates[phase].execute(workspace)"
    checks = [
        index
        for index in range(len(run))
        if run.startswith("_private_workspace_identity(workspace)", index)
    ]

    assert len(checks) >= 4
    assert checks[1] < run.index(execute) < checks[2]


def test_intermediate_workspace_entry_checks_surround_every_gate() -> None:
    source = (
        Path(__file__).parents[1] / "tools/controlled_release_preflight.py"
    ).read_text(encoding="utf-8")
    run = source[source.index("    def run(") : source.index("@contextmanager")]
    execute = "raw = self._gates[phase].execute(workspace)"
    checks = [
        index
        for index in range(len(run))
        if run.startswith("_verify_intermediate_workspace_entries(", index)
    ]

    assert len(checks) == 2
    assert checks[0] < run.index(execute) < checks[1]


def test_run_uses_child_identity_helper_only_for_new_mapped_output_capture() -> None:
    source = (
        Path(__file__).parents[1] / "tools/controlled_release_preflight.py"
    ).read_text(encoding="utf-8")
    run = source[source.index("    def run(") : source.index("@contextmanager")]

    assert run.count("_private_workspace_child_identity(") == 1
    assert "for name, identity in directory_identities.items():" not in run


def test_intermediate_workspace_verifier_accepts_only_captured_private_dirs(
    tmp_path: Path,
) -> None:
    identity = _private_workspace_identity(tmp_path)
    _verify_intermediate_workspace_entries(tmp_path, identity, {})
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(mode=0o700)
    artifact_identity = _private_workspace_child_identity(
        tmp_path, identity, "artifacts"
    )
    expected = {"artifacts": artifact_identity}
    _verify_intermediate_workspace_entries(tmp_path, identity, expected)
    artifacts.chmod(0o755)
    _rejected(
        lambda: _verify_intermediate_workspace_entries(
            tmp_path, identity, expected
        )
    )


def test_child_identity_capture_rejects_replacement_after_descriptor_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _private_workspace_identity(tmp_path)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(mode=0o700)
    original_stat = os.stat
    replaced = False

    def replacing_stat(path: object, *args: object, **kwargs: object) -> os.stat_result:
        nonlocal replaced
        if path == "artifacts" and not replaced:
            replaced = True
            artifacts.rmdir()
            artifacts.mkdir(mode=0o700)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(os, "stat", replacing_stat)

    _rejected(
        lambda: _private_workspace_child_identity(
            tmp_path, identity, "artifacts"
        )
    )
    assert replaced is True


def test_child_identity_capture_rechecks_terminal_child_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _private_workspace_identity(tmp_path)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(mode=0o700)
    original_stat = os.stat
    changed = False

    def changing_stat(path: object, *args: object, **kwargs: object) -> os.stat_result:
        nonlocal changed
        result = original_stat(path, *args, **kwargs)
        if path == "artifacts" and not changed:
            changed = True
            artifacts.chmod(0o755)
        return result

    monkeypatch.setattr(os, "stat", changing_stat)

    _rejected(
        lambda: _private_workspace_child_identity(
            tmp_path, identity, "artifacts"
        )
    )
    assert changed is True


def test_child_identity_capture_exhausts_and_normalizes_close_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _private_workspace_identity(tmp_path)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(mode=0o700)
    original_close = os.close
    closed: list[int] = []

    def failing_first_close(descriptor: int) -> None:
        closed.append(descriptor)
        original_close(descriptor)
        if len(closed) == 1:
            raise OSError("private capture close detail")

    monkeypatch.setattr(os, "close", failing_first_close)

    _rejected(
        lambda: _private_workspace_child_identity(
            tmp_path, identity, "artifacts"
        )
    )
    assert len(closed) == 2
    assert len(set(closed)) == 2


@pytest.mark.parametrize(
    ("workspace_identity", "name"),
    [
        ((True, 1), "artifacts"),
        ((1, -1), "artifacts"),
        ((1,), "artifacts"),
        ((1, 2, 3), "artifacts"),
        (("1", 2), "artifacts"),
        ((0, 0), "foreign"),
        ((0, 0), True),
        ((0, 0), ["artifacts"]),
    ],
)
def test_child_identity_capture_rejects_invalid_input_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    workspace_identity: object,
    name: object,
) -> None:
    monkeypatch.setattr(
        os,
        "open",
        lambda *args, **kwargs: pytest.fail("workspace must not be opened"),
    )

    _rejected(
        lambda: _private_workspace_child_identity(
            tmp_path,
            workspace_identity,  # type: ignore[arg-type]
            name,  # type: ignore[arg-type]
        )
    )


def test_intermediate_workspace_verifier_rejects_private_directory_replacement(
    tmp_path: Path,
) -> None:
    identity = _private_workspace_identity(tmp_path)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(mode=0o700)
    expected = {
        "artifacts": _private_workspace_child_identity(
            tmp_path, identity, "artifacts"
        )
    }
    _replace_empty_directory(artifacts)

    _rejected(
        lambda: _verify_intermediate_workspace_entries(
            tmp_path, identity, expected
        )
    )


def test_intermediate_workspace_verifier_rechecks_identity_after_relisting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _private_workspace_identity(tmp_path)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(mode=0o700)
    expected = {
        "artifacts": _private_workspace_child_identity(
            tmp_path, identity, "artifacts"
        )
    }
    original_listdir = os.listdir
    calls = 0

    def replacing_listdir(path: int) -> list[str]:
        nonlocal calls
        calls += 1
        if calls == 2:
            _replace_empty_directory(artifacts)
        return original_listdir(path)

    monkeypatch.setattr(os, "listdir", replacing_listdir)

    _rejected(
        lambda: _verify_intermediate_workspace_entries(
            tmp_path, identity, expected
        )
    )
    assert calls == 2


def test_intermediate_workspace_verifier_rejects_entry_after_terminal_child_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _private_workspace_identity(tmp_path)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(mode=0o700)
    expected = {
        "artifacts": _private_workspace_child_identity(
            tmp_path, identity, "artifacts"
        )
    }
    original_fstat = os.fstat
    calls = 0

    def polluting_fstat(descriptor: int) -> os.stat_result:
        nonlocal calls
        calls += 1
        result = original_fstat(descriptor)
        if calls == 3:
            (tmp_path / "foreign").write_bytes(b"data")
        return result

    monkeypatch.setattr(os, "fstat", polluting_fstat)

    _rejected(
        lambda: _verify_intermediate_workspace_entries(
            tmp_path, identity, expected
        )
    )
    assert calls == 3


def test_intermediate_workspace_verifier_snapshots_expected_identity_mapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _private_workspace_identity(tmp_path)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(mode=0o700)
    captured = _private_workspace_child_identity(
        tmp_path, identity, "artifacts"
    )
    expected = {"artifacts": captured}
    original_listdir = os.listdir
    mutated = False

    def mutating_listdir(path: int) -> list[str]:
        nonlocal mutated
        if not mutated:
            mutated = True
            expected["artifacts"] = (0, 0)
        return original_listdir(path)

    monkeypatch.setattr(os, "listdir", mutating_listdir)

    _verify_intermediate_workspace_entries(tmp_path, identity, expected)

    assert mutated is True
    assert expected["artifacts"] == (0, 0)


@pytest.mark.parametrize(
    "invalid_identity",
    [(True, 1), (1, -1), (1,), (1, 2, 3), ("1", 2)],
)
def test_intermediate_verifier_rejects_invalid_workspace_identity_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_identity: object,
) -> None:
    monkeypatch.setattr(
        os,
        "open",
        lambda *args, **kwargs: pytest.fail("workspace must not be opened"),
    )

    _rejected(
        lambda: _verify_intermediate_workspace_entries(
            tmp_path, invalid_identity, {}  # type: ignore[arg-type]
        )
    )


def test_intermediate_verifier_rejects_invalid_child_identity_before_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _private_workspace_identity(tmp_path)
    monkeypatch.setattr(
        os,
        "open",
        lambda *args, **kwargs: pytest.fail("workspace must not be opened"),
    )

    _rejected(
        lambda: _verify_intermediate_workspace_entries(
            tmp_path,
            identity,
            {"artifacts": (True, 1)},
        )
    )


@pytest.mark.parametrize(
    "expected",
    [
        {True: (1, 2)},
        {"artifacts": (1, 2), "bundle": (1, 2)},
    ],
)
def test_intermediate_verifier_rejects_invalid_identity_map_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    expected: dict[object, tuple[int, int]],
) -> None:
    identity = _private_workspace_identity(tmp_path)
    monkeypatch.setattr(
        os,
        "open",
        lambda *args, **kwargs: pytest.fail("workspace must not be opened"),
    )

    _rejected(
        lambda: _verify_intermediate_workspace_entries(
            tmp_path,
            identity,
            expected,  # type: ignore[arg-type]
        )
    )


def test_intermediate_verifier_rejects_workspace_identity_as_child_before_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _private_workspace_identity(tmp_path)
    monkeypatch.setattr(
        os,
        "open",
        lambda *args, **kwargs: pytest.fail("workspace must not be opened"),
    )

    _rejected(
        lambda: _verify_intermediate_workspace_entries(
            tmp_path,
            identity,
            {"artifacts": identity},
        )
    )


def test_intermediate_workspace_verifier_closes_retained_child_descriptors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _private_workspace_identity(tmp_path)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(mode=0o700)
    expected = {
        "artifacts": _private_workspace_child_identity(
            tmp_path, identity, "artifacts"
        )
    }
    original_close = os.close
    closed: list[int] = []

    def recording_close(descriptor: int) -> None:
        closed.append(descriptor)
        original_close(descriptor)

    monkeypatch.setattr(os, "close", recording_close)

    _verify_intermediate_workspace_entries(tmp_path, identity, expected)

    assert len(closed) == 2
    assert len(set(closed)) == 2


def test_intermediate_workspace_verifier_exhausts_and_normalizes_close_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _private_workspace_identity(tmp_path)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(mode=0o700)
    expected = {
        "artifacts": _private_workspace_child_identity(
            tmp_path, identity, "artifacts"
        )
    }
    original_close = os.close
    closed: list[int] = []

    def failing_first_close(descriptor: int) -> None:
        closed.append(descriptor)
        original_close(descriptor)
        if len(closed) == 1:
            raise OSError("private close detail")

    monkeypatch.setattr(os, "close", failing_first_close)

    _rejected(
        lambda: _verify_intermediate_workspace_entries(
            tmp_path, identity, expected
        )
    )
    assert len(closed) == 2
    assert len(set(closed)) == 2


@pytest.mark.parametrize("mutation", ["extra", "missing", "symlink"])
def test_terminal_workspace_inventory_rejects_topology_drift(
    tmp_path: Path, mutation: str
) -> None:
    for name, kind in WORKSPACE_INVENTORY.items():
        target = tmp_path / name
        if kind == "directory":
            target.mkdir(mode=0o700)
        else:
            target.write_bytes(b"evidence\n")
            target.chmod(0o600)
    if mutation == "extra":
        (tmp_path / "extra").mkdir(mode=0o700)
    elif mutation == "missing":
        (tmp_path / "bundle").rmdir()
    else:
        (tmp_path / "bundle").rmdir()
        (tmp_path / "bundle").symlink_to(tmp_path / "artifacts")
    identity = (tmp_path.stat().st_dev, tmp_path.stat().st_ino)

    _rejected(lambda: _verify_private_workspace_inventory(tmp_path, identity))


def test_terminal_workspace_inventory_rejects_bound_child_replacement(
    tmp_path: Path,
) -> None:
    for name, kind in WORKSPACE_INVENTORY.items():
        target = tmp_path / name
        if kind == "directory":
            target.mkdir(mode=0o700)
        else:
            target.write_bytes(b"evidence\n")
            target.chmod(0o600)
    workspace_identity = _private_workspace_identity(tmp_path)
    identities = {
        name: _private_workspace_child_identity(tmp_path, workspace_identity, name)
        for name in PHASE_OUTPUT_DIRECTORIES.values()
    }
    bundle = tmp_path / "bundle"
    _replace_empty_directory(bundle)

    _rejected(
        lambda: _verify_private_workspace_inventory(
            tmp_path,
            workspace_identity,
            expected_directory_identities=identities,
        )
    )


def test_bound_child_descriptor_set_rejects_extra_workspace_entry(
    tmp_path: Path,
) -> None:
    for name, kind in WORKSPACE_INVENTORY.items():
        target = tmp_path / name
        if kind == "directory":
            target.mkdir(mode=0o700)
        else:
            target.write_bytes(b"evidence\n")
            target.chmod(0o600)
    workspace_identity = _private_workspace_identity(tmp_path)
    identities = {
        name: _private_workspace_child_identity(tmp_path, workspace_identity, name)
        for name in PHASE_OUTPUT_DIRECTORIES.values()
    }
    descriptor = controlled.os.open(
        tmp_path,
        controlled.os.O_RDONLY
        | controlled.os.O_DIRECTORY
        | controlled.os.O_NOFOLLOW,
    )
    try:
        _verify_bound_child_directory_identities(descriptor, identities)
        (tmp_path / "foreign").mkdir(mode=0o700)
        _rejected(
            lambda: _verify_bound_child_directory_identities(
                descriptor, identities
            )
        )
    finally:
        controlled.os.close(descriptor)


def test_receipt_cannot_claim_another_phase_or_commit(tmp_path: Path) -> None:
    calls: list[str] = []
    gates = _gates(calls)
    gates["wheel"] = Gate("wheel", calls, _receipt("sdist"))
    _rejected(lambda: ControlledReleasePreflight(gates).run(tmp_path / "phase"))

    calls.clear()
    gates = _gates(calls)
    gates["wheel"] = Gate("wheel", calls, _receipt("wheel", commit="b" * 40))
    _rejected(lambda: ControlledReleasePreflight(gates).run(tmp_path / "commit"))


def test_missing_extra_or_noncanonical_receipt_is_rejected(tmp_path: Path) -> None:
    calls: list[str] = []
    missing = _gates(calls)
    del missing["bundle"]
    _rejected(lambda: ControlledReleasePreflight(missing))

    extra = _gates(calls)
    extra["publish"] = Gate("publish", calls)
    _rejected(lambda: ControlledReleasePreflight(extra))

    malformed = _gates(calls)
    malformed["runtime"] = Gate(
        "runtime", calls, _receipt("runtime").replace(b'"phase"', b' "phase"')
    )
    _rejected(lambda: ControlledReleasePreflight(malformed).run(tmp_path / "bad"))


@pytest.mark.parametrize(
    "value", [b"", b"x" * (MAX_GATE_RECEIPT_BYTES + 1)]
)
def test_gate_receipt_rejects_invalid_size_before_parsing(value: bytes) -> None:
    _rejected(lambda: GateReceipt.parse(value, "runtime"))


def test_gate_receipt_rejects_phase_outside_fixed_inventory() -> None:
    _rejected(lambda: GateReceipt.parse(_receipt("runtime"), "publish"))


def test_gate_receipt_size_guard_precedes_json_parsing() -> None:
    source = (
        Path(__file__).parents[1] / "tools/controlled_release_preflight.py"
    ).read_text(encoding="utf-8")
    parser = source[
        source.index("class GateReceipt") : source.index("class BuildGate")
    ]

    assert parser.index("len(value) > MAX_GATE_RECEIPT_BYTES") < parser.index(
        "json.loads(value)"
    )


def test_existing_output_is_never_overwritten(tmp_path: Path) -> None:
    output = tmp_path / "result"
    output.mkdir()
    marker = output / "owner-data"
    marker.write_text("preserve", encoding="ascii")

    _rejected(lambda: ControlledReleasePreflight(_gates([])).run(output))

    assert marker.read_text(encoding="ascii") == "preserve"


def test_symbolic_output_is_rejected_without_touching_its_target(tmp_path: Path) -> None:
    target = tmp_path / "owner-target"
    target.mkdir()
    marker = target / "owner-data"
    marker.write_text("preserve", encoding="ascii")
    output = tmp_path / "result"
    output.symlink_to(target, target_is_directory=True)

    _rejected(lambda: ControlledReleasePreflight(_gates([])).run(output))

    assert output.is_symlink()
    assert marker.read_text(encoding="ascii") == "preserve"


def test_output_parent_must_be_private_and_no_follow(tmp_path: Path) -> None:
    output = tmp_path / "result"
    tmp_path.chmod(0o755)

    _rejected(lambda: _private_output_parent_identity(output))


def test_workspace_publication_is_relative_to_bound_parent(tmp_path: Path) -> None:
    source = tmp_path / "workspace"
    source.mkdir(mode=0o700)
    output = tmp_path / "result"
    parent_identity = _private_output_parent_identity(output)
    workspace_identity = (source.stat().st_dev, source.stat().st_ino)

    _publish_private_workspace(
        source,
        output,
        parent_identity=parent_identity,
        workspace_identity=workspace_identity,
    )

    assert not source.exists()
    assert output.is_dir()


def test_workspace_publication_rejects_replaced_bound_child(tmp_path: Path) -> None:
    source = tmp_path / "workspace"
    source.mkdir(mode=0o700)
    for name in PHASE_OUTPUT_DIRECTORIES.values():
        (source / name).mkdir(mode=0o700)
    evidence_path = source / EVIDENCE_NAME
    evidence_path.write_bytes(b"evidence\n")
    evidence_path.chmod(0o600)
    workspace_identity = _private_workspace_identity(source)
    identities = {
        name: _private_workspace_child_identity(source, workspace_identity, name)
        for name in PHASE_OUTPUT_DIRECTORIES.values()
    }
    bundle = source / "bundle"
    _replace_empty_directory(bundle)
    output = tmp_path / "result"

    _rejected(
        lambda: _publish_private_workspace(
            source,
            output,
            parent_identity=_private_output_parent_identity(output),
            workspace_identity=workspace_identity,
            expected_directory_identities=identities,
        )
    )

    assert source.is_dir()
    assert not output.exists()


def test_workspace_publication_preserves_target_created_before_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "workspace"
    source.mkdir(mode=0o700)
    for name in PHASE_OUTPUT_DIRECTORIES.values():
        (source / name).mkdir(mode=0o700)
    evidence = source / EVIDENCE_NAME
    evidence.write_bytes(b"evidence\n")
    evidence.chmod(0o600)
    workspace_identity = _private_workspace_identity(source)
    identities = {
        name: _private_workspace_child_identity(source, workspace_identity, name)
        for name in PHASE_OUTPUT_DIRECTORIES.values()
    }
    output = tmp_path / "result"
    original = controlled._verify_bound_child_directory_identities

    def create_target_after_child_check(
        descriptor: int, expected: dict[str, tuple[int, int]]
    ) -> None:
        original(descriptor, expected)
        output.mkdir(mode=0o700)
        (output / "owner-data").write_bytes(b"preserve")

    monkeypatch.setattr(
        controlled,
        "_verify_bound_child_directory_identities",
        create_target_after_child_check,
    )

    _rejected(
        lambda: _publish_private_workspace(
            source,
            output,
            parent_identity=_private_output_parent_identity(output),
            workspace_identity=workspace_identity,
            expected_directory_identities=identities,
        )
    )

    assert source.is_dir()
    assert (output / "owner-data").read_bytes() == b"preserve"


def test_post_rename_verification_failure_restores_private_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "workspace"
    source.mkdir(mode=0o700)
    for name in PHASE_OUTPUT_DIRECTORIES.values():
        (source / name).mkdir(mode=0o700)
    evidence_path = source / EVIDENCE_NAME
    evidence_path.write_bytes(b"evidence\n")
    evidence_path.chmod(0o600)
    workspace_identity = _private_workspace_identity(source)
    identities = {
        name: _private_workspace_child_identity(source, workspace_identity, name)
        for name in PHASE_OUTPUT_DIRECTORIES.values()
    }
    output = tmp_path / "result"
    original = controlled._verify_bound_child_directory_identities
    calls = 0

    def fail_second_verification(*args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ControlledPreflightRejected("controlled release preflight rejected")
        original(*args, **kwargs)

    monkeypatch.setattr(
        controlled,
        "_verify_bound_child_directory_identities",
        fail_second_verification,
    )

    _rejected(
        lambda: _publish_private_workspace(
            source,
            output,
            parent_identity=_private_output_parent_identity(output),
            workspace_identity=workspace_identity,
            expected_directory_identities=identities,
        )
    )

    assert calls == 2
    assert source.is_dir()
    assert not output.exists()


def test_published_evidence_failure_restores_private_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "workspace"
    source.mkdir(mode=0o700)
    for name in PHASE_OUTPUT_DIRECTORIES.values():
        (source / name).mkdir(mode=0o700)
    evidence = b"evidence\n"
    evidence_path = source / EVIDENCE_NAME
    evidence_path.write_bytes(evidence)
    evidence_path.chmod(0o600)
    workspace_identity = _private_workspace_identity(source)
    identities = {
        name: _private_workspace_child_identity(source, workspace_identity, name)
        for name in PHASE_OUTPUT_DIRECTORIES.values()
    }
    output = tmp_path / "result"

    def reject_readback(*args: object, **kwargs: object) -> None:
        raise ControlledPreflightRejected("controlled release preflight rejected")

    monkeypatch.setattr(
        controlled, "_verify_private_workspace_evidence", reject_readback
    )

    _rejected(
        lambda: _publish_private_workspace(
            source,
            output,
            parent_identity=_private_output_parent_identity(output),
            workspace_identity=workspace_identity,
            expected_directory_identities=identities,
            expected_evidence=evidence,
        )
    )

    assert source.is_dir()
    assert not output.exists()


def test_publication_parent_sync_failure_restores_private_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "workspace"
    source.mkdir(mode=0o700)
    output = tmp_path / "result"
    parent_identity = _private_output_parent_identity(output)
    workspace_identity = _private_workspace_identity(source)
    original_fsync = controlled.os.fsync
    calls = 0

    def fail_forward_sync(descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("sync rejected")
        original_fsync(descriptor)

    monkeypatch.setattr(controlled.os, "fsync", fail_forward_sync)

    _rejected(
        lambda: _publish_private_workspace(
            source,
            output,
            parent_identity=parent_identity,
            workspace_identity=workspace_identity,
        )
    )

    assert calls == 2
    assert source.is_dir()
    assert not output.exists()


@pytest.mark.parametrize("mutation", ["parent_mode", "output_mode"])
def test_terminal_publication_metadata_drift_restores_private_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    source = tmp_path / "workspace"
    source.mkdir(mode=0o700)
    for name in PHASE_OUTPUT_DIRECTORIES.values():
        (source / name).mkdir(mode=0o700)
    evidence_path = source / EVIDENCE_NAME
    evidence_path.write_bytes(b"evidence\n")
    evidence_path.chmod(0o600)
    workspace_identity = _private_workspace_identity(source)
    identities = {
        name: _private_workspace_child_identity(source, workspace_identity, name)
        for name in PHASE_OUTPUT_DIRECTORIES.values()
    }
    output = tmp_path / "result"
    original = controlled._verify_bound_child_directory_identities
    calls = 0

    def mutate_after_second_verification(
        descriptor: int, expected: dict[str, tuple[int, int]]
    ) -> None:
        nonlocal calls
        calls += 1
        original(descriptor, expected)
        if calls == 2:
            if mutation == "parent_mode":
                tmp_path.chmod(0o755)
            else:
                controlled.os.fchmod(descriptor, 0o755)

    monkeypatch.setattr(
        controlled,
        "_verify_bound_child_directory_identities",
        mutate_after_second_verification,
    )

    _rejected(
        lambda: _publish_private_workspace(
            source,
            output,
            parent_identity=_private_output_parent_identity(output),
            workspace_identity=workspace_identity,
            expected_directory_identities=identities,
        )
    )

    tmp_path.chmod(0o700)
    source.chmod(0o700)
    assert source.is_dir()
    assert not output.exists()


def test_workspace_publication_uses_one_parent_descriptor() -> None:
    source = (
        Path(__file__).parents[1] / "tools/controlled_release_preflight.py"
    ).read_text(encoding="utf-8")
    publication = source[
        source.index("def _publish_private_workspace") : source.index("@dataclass")
    ]

    assert "os.O_DIRECTORY | os.O_NOFOLLOW" in publication
    assert "src_dir_fd=descriptor" in publication
    assert "dst_dir_fd=descriptor" in publication
    assert ".replace(" not in publication


def test_workspace_publication_checks_children_before_and_after_rename() -> None:
    source = (
        Path(__file__).parents[1] / "tools/controlled_release_preflight.py"
    ).read_text(encoding="utf-8")
    publication = source[
        source.index("def _publish_private_workspace") : source.index("@dataclass")
    ]
    verify = "_verify_bound_child_directory_identities("

    assert publication.count(verify) == 2
    assert publication.index(verify) < publication.index("os.rename(")
    assert publication.rindex(verify) > publication.index("os.rename(")
    assert "expected_directory_identities=directory_identities" in source


def test_publication_rechecks_namespace_immediately_before_rename() -> None:
    source = (
        Path(__file__).parents[1] / "tools/controlled_release_preflight.py"
    ).read_text(encoding="utf-8")
    publication = source[
        source.index("def _publish_private_workspace") : source.index("@dataclass")
    ]
    child_check = publication.index("_verify_bound_child_directory_identities(")
    parent_check = publication.index("parent_before_commit = os.fstat(descriptor)")
    source_check = publication.index("source_before_commit = os.stat(")
    absence_check = publication.index(
        "os.stat(output.name, dir_fd=descriptor", source_check
    )
    rename = publication.index("os.rename(")

    assert child_check < parent_check < source_check < absence_check < rename
    assert "!= parent_identity" in publication[parent_check:rename]
    assert "!= workspace_identity" in publication[source_check:rename]


def test_post_rename_failure_rollback_is_identity_bound_and_relative() -> None:
    source = (
        Path(__file__).parents[1] / "tools/controlled_release_preflight.py"
    ).read_text(encoding="utf-8")
    rollback = source[
        source.index("def _rollback_private_workspace_publication") : source.index(
            "def _publish_private_workspace"
        )
    ]

    assert "(output.st_dev, output.st_ino) != workspace_identity" in rollback
    assert "(parent.st_dev, parent.st_ino) != parent_identity" in rollback
    assert "src_dir_fd=parent_descriptor" in rollback
    assert "dst_dir_fd=parent_descriptor" in rollback
    assert "os.fsync(parent_descriptor)" in rollback
    assert "(restored.st_dev, restored.st_ino) == workspace_identity" in rollback
    assert "(parent_after.st_dev, parent_after.st_ino) == parent_identity" in rollback


def test_publication_rollback_rejects_wrong_parent_identity(tmp_path: Path) -> None:
    output = tmp_path / "result"
    output.mkdir(mode=0o700)
    workspace_identity = _private_workspace_identity(output)
    descriptor = controlled.os.open(
        tmp_path,
        controlled.os.O_RDONLY
        | controlled.os.O_DIRECTORY
        | controlled.os.O_NOFOLLOW,
    )
    try:
        restored = controlled._rollback_private_workspace_publication(
            descriptor,
            parent_identity=(0, 0),
            workspace_name="workspace",
            output_name=output.name,
            workspace_identity=workspace_identity,
        )
    finally:
        controlled.os.close(descriptor)

    assert restored is False
    assert output.is_dir()
    assert not (tmp_path / "workspace").exists()


def test_publication_rollback_reports_verified_restoration(tmp_path: Path) -> None:
    output = tmp_path / "result"
    output.mkdir(mode=0o700)
    workspace_identity = _private_workspace_identity(output)
    parent_identity = _private_output_parent_identity(tmp_path / "unused")
    descriptor = controlled.os.open(
        tmp_path,
        controlled.os.O_RDONLY
        | controlled.os.O_DIRECTORY
        | controlled.os.O_NOFOLLOW,
    )
    try:
        restored = controlled._rollback_private_workspace_publication(
            descriptor,
            parent_identity=parent_identity,
            workspace_name="workspace",
            output_name=output.name,
            workspace_identity=workspace_identity,
        )
    finally:
        controlled.os.close(descriptor)

    assert restored is True
    assert (tmp_path / "workspace").is_dir()
    assert not output.exists()


def test_publication_terminally_rechecks_evidence_and_inventory() -> None:
    source = (
        Path(__file__).parents[1] / "tools/controlled_release_preflight.py"
    ).read_text(encoding="utf-8")
    publication = source[
        source.index("def _publish_private_workspace") : source.index("@dataclass")
    ]
    rename = publication.index("os.rename(")

    assert publication.index("_verify_private_workspace_evidence(") > rename
    assert publication.index("_verify_private_workspace_inventory(") > rename
    assert "expected_evidence=evidence_payload" in source


def test_publication_syncs_and_terminally_rebinds_parent_namespace() -> None:
    source = (
        Path(__file__).parents[1] / "tools/controlled_release_preflight.py"
    ).read_text(encoding="utf-8")
    publication = source[
        source.index("def _publish_private_workspace") : source.index("@dataclass")
    ]
    rename = publication.index("os.rename(")

    assert publication.index("os.fsync(descriptor)") > rename
    assert publication.index("parent_after = os.fstat(descriptor)") > rename
    assert "(parent_after.st_dev, parent_after.st_ino) != parent_identity" in publication
    assert "(output_after.st_dev, output_after.st_ino) != workspace_identity" in publication
    assert "os.stat(workspace.name, dir_fd=descriptor" in publication


def test_publication_terminally_rechecks_private_root_metadata() -> None:
    source = (
        Path(__file__).parents[1] / "tools/controlled_release_preflight.py"
    ).read_text(encoding="utf-8")
    publication = source[
        source.index("def _publish_private_workspace") : source.index("@dataclass")
    ]

    assert "stat.S_IMODE(parent_after.st_mode) != 0o700" in publication
    assert "parent_after.st_uid != os.getuid()" in publication
    assert "stat.S_IMODE(output_after.st_mode) != 0o700" in publication
    assert "output_after.st_uid != os.getuid()" in publication


def test_bound_child_verification_keeps_no_follow_descriptors_open() -> None:
    source = (
        Path(__file__).parents[1] / "tools/controlled_release_preflight.py"
    ).read_text(encoding="utf-8")
    verifier = source[
        source.index("def _verify_bound_child_directory_identities") : source.index(
            "def _rollback_private_workspace_publication"
        )
    ]

    assert "os.O_DIRECTORY | os.O_NOFOLLOW" in verifier
    assert "descriptors.append((child_descriptor, identity))" in verifier
    assert verifier.count("os.fstat(child_descriptor)") == 2
    assert "sorted(os.listdir(workspace_descriptor)) != names" in verifier
    assert "os.close(child_descriptor)" in verifier


def test_private_workspace_evidence_never_replaces_existing_file(
    tmp_path: Path,
) -> None:
    existing = tmp_path / EVIDENCE_NAME
    existing.write_bytes(b"owner-data")

    _rejected(lambda: _write_private_workspace_evidence(tmp_path, b"evidence\n"))

    assert existing.read_bytes() == b"owner-data"


def test_byte_identical_workspace_evidence_replacement_fails_identity_checks(
    tmp_path: Path,
) -> None:
    for name in PHASE_OUTPUT_DIRECTORIES.values():
        (tmp_path / name).mkdir(mode=0o700)
    payload = b"evidence\n"
    evidence = tmp_path / EVIDENCE_NAME
    evidence.write_bytes(payload)
    evidence.chmod(0o600)
    evidence_identity = _verify_private_workspace_evidence(tmp_path, payload)
    workspace_identity = _private_workspace_identity(tmp_path)
    directory_identities = {
        name: _private_workspace_child_identity(tmp_path, workspace_identity, name)
        for name in PHASE_OUTPUT_DIRECTORIES.values()
    }
    _replace_file(evidence, payload, mode=0o600)

    _rejected(
        lambda: _verify_private_workspace_evidence(
            tmp_path, payload, expected_identity=evidence_identity
        )
    )
    _rejected(
        lambda: _verify_private_workspace_inventory(
            tmp_path,
            workspace_identity,
            expected_directory_identities=directory_identities,
            expected_evidence_identity=evidence_identity,
        )
    )


def test_evidence_writer_returns_identity_from_created_descriptor(
    tmp_path: Path,
) -> None:
    payload = b"evidence\n"

    evidence, identity = controlled._write_private_workspace_evidence_with_identity(
        tmp_path, payload
    )

    metadata = evidence.stat()
    assert identity == (metadata.st_dev, metadata.st_ino)
    assert _verify_private_workspace_evidence(
        tmp_path, payload, expected_identity=identity
    ) == identity


def test_evidence_writer_rejects_replaced_bound_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(mode=0o700)
    identity = _private_workspace_identity(workspace)
    _replace_empty_directory(workspace)

    _rejected(
        lambda: controlled._write_private_workspace_evidence_with_identity(
            workspace,
            b"evidence\n",
            expected_workspace_identity=identity,
        )
    )

    assert list(workspace.iterdir()) == []


def test_evidence_writer_failure_removes_only_its_created_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_write = controlled.os.write

    def reject_write(descriptor: int, payload: object) -> int:
        raise OSError("write rejected")

    monkeypatch.setattr(controlled.os, "write", reject_write)

    _rejected(
        lambda: controlled._write_private_workspace_evidence_with_identity(
            tmp_path, b"evidence\n"
        )
    )

    monkeypatch.setattr(controlled.os, "write", original_write)
    assert list(tmp_path.iterdir()) == []


def test_evidence_writer_failure_preserves_replacement_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def replace_then_reject(descriptor: int, payload: object) -> int:
        evidence = tmp_path / EVIDENCE_NAME
        evidence.unlink()
        evidence.write_bytes(b"replacement")
        evidence.chmod(0o600)
        raise OSError("write rejected")

    monkeypatch.setattr(controlled.os, "write", replace_then_reject)

    _rejected(
        lambda: controlled._write_private_workspace_evidence_with_identity(
            tmp_path, b"evidence\n"
        )
    )

    assert (tmp_path / EVIDENCE_NAME).read_bytes() == b"replacement"


def test_evidence_writer_cleanup_preserves_file_after_workspace_mode_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def change_parent_then_reject(descriptor: int, payload: object) -> int:
        tmp_path.chmod(0o755)
        raise OSError("write rejected")

    monkeypatch.setattr(controlled.os, "write", change_parent_then_reject)

    _rejected(
        lambda: controlled._write_private_workspace_evidence_with_identity(
            tmp_path, b"evidence\n"
        )
    )

    tmp_path.chmod(0o700)
    evidence = tmp_path / EVIDENCE_NAME
    assert evidence.is_file()
    assert evidence.read_bytes() == b""


def test_evidence_reader_rejects_same_file_moved_to_replaced_workspace(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(mode=0o700)
    payload = b"evidence\n"
    evidence, evidence_identity = (
        controlled._write_private_workspace_evidence_with_identity(
            workspace, payload
        )
    )
    workspace_identity = _private_workspace_identity(workspace)
    displaced = tmp_path / "displaced"
    workspace.rename(displaced)
    workspace.mkdir(mode=0o700)
    (displaced / EVIDENCE_NAME).rename(workspace / EVIDENCE_NAME)

    _rejected(
        lambda: _verify_private_workspace_evidence(
            workspace,
            payload,
            expected_identity=evidence_identity,
            expected_workspace_identity=workspace_identity,
        )
    )


def test_private_workspace_evidence_uses_relative_no_follow_write() -> None:
    source = (
        Path(__file__).parents[1] / "tools/controlled_release_preflight.py"
    ).read_text(encoding="utf-8")
    writer = source[
        source.index("def _write_private_workspace_evidence") : source.index(
            "@dataclass"
        )
    ]

    assert "os.O_DIRECTORY | os.O_NOFOLLOW" in writer
    assert "os.O_EXCL | os.O_NOFOLLOW" in writer
    assert "dir_fd=directory_descriptor" in writer
    assert ".write_bytes(" not in writer


def test_controlled_evidence_identity_crosses_publication_boundary() -> None:
    source = (
        Path(__file__).parents[1] / "tools/controlled_release_preflight.py"
    ).read_text(encoding="utf-8")
    run = source[source.index("    def run(") : source.index("@contextmanager")]
    publication = source[
        source.index("def _publish_private_workspace") : source.index("@dataclass")
    ]

    assert "evidence_path, evidence_identity = (" in run
    assert "_write_private_workspace_evidence_with_identity(" in run
    assert "expected_identity=evidence_identity" in run
    assert "verified_evidence_identity != evidence_identity" in run
    assert "expected_evidence_identity=evidence_identity" in run
    assert "expected_workspace_identity=workspace_identity" in run
    assert "expected_identity=expected_evidence_identity" in publication
    assert "expected_evidence_identity=expected_evidence_identity" in publication


def test_evidence_writer_checks_bound_workspace_before_and_after_write() -> None:
    source = (
        Path(__file__).parents[1] / "tools/controlled_release_preflight.py"
    ).read_text(encoding="utf-8")
    writer = source[
        source.index("def _write_private_workspace_evidence_with_identity") : source.index(
            "def _verify_private_workspace_evidence"
        )
    ]

    assert writer.count("expected_workspace_identity is not None") == 2
    assert "(directory_metadata.st_dev, directory_metadata.st_ino)" in writer
    assert "(after.st_dev, after.st_ino) != expected_workspace_identity" in writer


def test_evidence_writer_cleanup_is_created_identity_bound() -> None:
    source = (
        Path(__file__).parents[1] / "tools/controlled_release_preflight.py"
    ).read_text(encoding="utf-8")
    cleanup = source[
        source.index("def _unlink_created_workspace_evidence") : source.index(
            "def _write_private_workspace_evidence"
        )
    ]
    writer = source[
        source.index("def _write_private_workspace_evidence_with_identity") : source.index(
            "def _verify_private_workspace_evidence"
        )
    ]

    assert "(current.st_dev, current.st_ino) != expected_identity" in cleanup
    assert "os.unlink(EVIDENCE_NAME, dir_fd=directory_descriptor)" in cleanup
    assert "os.fsync(directory_descriptor)" in cleanup
    assert "(parent.st_dev, parent.st_ino) != expected_workspace_identity" in cleanup
    assert "stat.S_IMODE(parent.st_mode) != 0o700" in cleanup
    assert "parent.st_uid != os.getuid()" in cleanup
    assert "(parent_after.st_dev, parent_after.st_ino)" in cleanup
    assert "created_identity = (created_metadata.st_dev, created_metadata.st_ino)" in writer
    assert writer.count("_unlink_created_workspace_evidence(") == 2


def test_evidence_reader_checks_bound_workspace_before_and_after_read() -> None:
    source = (
        Path(__file__).parents[1] / "tools/controlled_release_preflight.py"
    ).read_text(encoding="utf-8")
    reader = source[
        source.index("def _verify_private_workspace_evidence") : source.index(
            "def _private_workspace_identity"
        )
    ]
    run = source[source.index("    def run(") : source.index("@contextmanager")]
    publication = source[
        source.index("def _publish_private_workspace") : source.index("@dataclass")
    ]

    assert reader.count("expected_workspace_identity is not None") == 2
    assert "(directory_metadata.st_dev, directory_metadata.st_ino)" in reader
    assert "(directory_after.st_dev, directory_after.st_ino)" in reader
    assert "expected_workspace_identity=workspace_identity" in run
    assert "expected_workspace_identity=workspace_identity" in publication


def test_private_workspace_evidence_rejects_oversized_payload(tmp_path: Path) -> None:
    _rejected(
        lambda: _write_private_workspace_evidence(
            tmp_path, b"x" * (MAX_CONTROLLED_EVIDENCE_BYTES + 1)
        )
    )
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("mutation", ["bytes", "mode", "hardlink", "symlink"])
def test_terminal_private_evidence_check_rejects_drift(
    tmp_path: Path, mutation: str
) -> None:
    payload = b"evidence\n"
    evidence = _write_private_workspace_evidence(tmp_path, payload)
    if mutation == "bytes":
        evidence.write_bytes(b"changed!\n")
        evidence.chmod(0o600)
    elif mutation == "mode":
        evidence.chmod(0o644)
    elif mutation == "hardlink":
        (tmp_path / "second-name").hardlink_to(evidence)
    else:
        outside = tmp_path / "outside"
        outside.write_bytes(payload)
        evidence.unlink()
        evidence.symlink_to(outside)

    _rejected(lambda: _verify_private_workspace_evidence(tmp_path, payload))
