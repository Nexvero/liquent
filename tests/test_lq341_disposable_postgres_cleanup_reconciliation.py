from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

import liquent_platform.operators.disposable_postgres_cleanup_reconcile as reconcile
from liquent_platform.operators.disposable_postgres_runtime_cleanup import _binding
from liquent_platform.operators.staging_process_adapter import ProcessObservation
from tests.test_lq330_disposable_postgres_composition import _inspection, _model
from tests.test_lq331_disposable_postgres_reconciliation import (
    CONTAINER, NETWORKS, NOW, PROJECT, VOLUME, _volume,
)
from tests.test_lq337_disposable_postgres_cleanup_preflight import _inputs
from tests.test_lq339_disposable_postgres_runtime_cleanup import _network


class Processes:
    def __init__(self, values):
        self.values, self.calls = list(values), []

    def run(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        return self.values.pop(0)


def _observation(stdout: bytes = b"", *, timed_out: bool = False):
    return ProcessObservation(0, stdout, b"", timed_out, False, False)


def _private(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    os.chmod(path, 0o600)
    return path


def _empty_network(name: str) -> bytes:
    value = json.loads(_network(name))
    value[0]["Containers"] = {}
    return json.dumps(value).encode()


def _container(*, running: bool) -> bytes:
    value = json.loads(_inspection())[0]
    value["Name"] = f"/{CONTAINER}"
    if running:
        value["State"]["Running"] = True
    else:
        value["State"] = {"Running": False, "Status": "exited"}
    return json.dumps([value]).encode()


def _processes(state: str) -> Processes:
    presence = {
        "runtime_intact": (True, True, True),
        "container_stopped": (True, True, True),
        "container_removed": (False, True, True),
        "application_network_removed": (False, False, True),
        "runtime_removed_evidence_missing": (False, False, False),
        "conflict": (False, True, False),
    }[state]
    values = [_observation(_model())]
    for present, name in zip(presence + (True,), (CONTAINER, *NETWORKS, VOLUME), strict=True):
        values.append(_observation((name + "\n").encode() if present else b""))
    values.append(_observation(_volume()))
    if presence[0]:
        values.extend([
            _observation(_container(running=state == "runtime_intact")),
            _observation(_network(NETWORKS[0])),
            _observation(_network(NETWORKS[1])),
        ])
    else:
        if presence[1]:
            values.append(_observation(_empty_network(NETWORKS[0])))
        if presence[2]:
            values.append(_observation(_empty_network(NETWORKS[1])))
    return Processes(values)


def _setup(tmp_path: Path, state: str = "runtime_intact", *, claim: bool = True):
    values = _inputs(tmp_path, scope="runtime_only")
    cleanup = json.loads(values["cleanup_file"].read_text())
    current = _private(tmp_path / "cleanup-reconciliation.json", {
        "schema_version": 1,
        "cleanup_reconciliation_id": "cleanup-reconciliation-341",
        "cleanup_id": cleanup["cleanup_id"], "run_id": cleanup["run_id"],
        "phase": "disposable_postgres", "source_commit": cleanup["source_commit"],
        "image_ref": cleanup["image_ref"], "compose_sha256": cleanup["compose_sha256"],
        "reconciliation_id": cleanup["reconciliation_id"],
        "claim_reconciliation_id": cleanup["claim_reconciliation_id"],
        "disposition_id": cleanup["disposition_id"],
        "staging_evidence_sha256": cleanup["staging_evidence_sha256"],
        "reconciliation_evidence_sha256": cleanup["reconciliation_evidence_sha256"],
        "claim_reconciliation_evidence_sha256": cleanup["claim_reconciliation_evidence_sha256"],
        "disposition_authorization_sha256": cleanup["disposition_authorization_sha256"],
        "cleanup_authorization_sha256": hashlib.sha256(values["cleanup_file"].read_bytes()).hexdigest(),
        "operation": "inspect_disposable_postgres_runtime_cleanup", "scope": "runtime_only",
        "executor_id": "cleanup-reconcile-executor",
        "authorizer_id": "cleanup-reconcile-authorizer",
        "valid_from": "2026-08-20T13:30:00Z", "valid_until": "2026-08-20T14:30:00Z",
    })
    original = reconcile._historical(values["authorization_file"])
    binding = _binding(original, cleanup, values["cleanup_file"], PROJECT)
    stem = hashlib.sha256(cleanup["cleanup_id"].encode()).hexdigest()
    claim_path = values["evidence_directory"] / f".postgres-cleanup-{stem}.claim"
    final = values["evidence_directory"] / f"postgres-cleanup-{stem}.json"
    if claim:
        _private(claim_path, dict(binding, started_at="2026-08-20T14:00:00Z"))
    values.update({
        "cleanup_reconciliation_file": current,
        "processes": _processes(state), "clock": lambda: NOW,
    })
    return values, binding, claim_path, final


@pytest.mark.parametrize("state", [
    "runtime_intact", "container_stopped", "container_removed",
    "application_network_removed", "runtime_removed_evidence_missing",
])
def test_closed_cleanup_sequence_states_are_classified_read_only(tmp_path: Path, state: str) -> None:
    values, _, claim, _ = _setup(tmp_path, state)
    result = reconcile.reconcile_disposable_postgres_cleanup(**values)
    assert json.loads(result)["outcome"] == state
    assert claim.exists()
    forbidden = {"stop", "start", "rm", "remove", "disconnect", "down", "prune", "kill"}
    assert not any(set(call[0]) & forbidden for call in values["processes"].calls)


def test_impossible_prefix_is_conflict_without_mutation(tmp_path: Path) -> None:
    values, _, claim, _ = _setup(tmp_path, "conflict")
    result = reconcile.reconcile_disposable_postgres_cleanup(**values)
    assert json.loads(result)["outcome"] == "conflict"
    assert claim.exists()


def test_final_evidence_precedes_claim_and_docker(tmp_path: Path) -> None:
    values, binding, claim, final = _setup(tmp_path)
    _private(final, dict(
        binding, outcome="removed_runtime", started_at="2026-08-20T14:00:00Z",
        completed_at="2026-08-20T14:01:00Z",
    ))
    values["processes"] = Processes([])
    result = reconcile.reconcile_disposable_postgres_cleanup(**values)
    assert json.loads(result)["outcome"] == "final_evidence_present"
    assert claim.exists() and values["processes"].calls == []


def test_absent_claim_and_evidence_is_not_found_without_docker(tmp_path: Path) -> None:
    values, _, _, _ = _setup(tmp_path, claim=False)
    values["processes"] = Processes([])
    result = reconcile.reconcile_disposable_postgres_cleanup(**values)
    assert json.loads(result)["outcome"] == "not_found"
    assert values["processes"].calls == []


def test_mismatched_claim_or_technical_docker_result_is_unavailable(tmp_path: Path) -> None:
    values, _, claim, _ = _setup(tmp_path)
    record = json.loads(claim.read_text())
    record["run_id"] = "other-run"
    _private(claim, record)
    values["processes"] = Processes([])
    with pytest.raises(reconcile.DisposablePostgresCleanupReconcileUnavailable):
        reconcile.reconcile_disposable_postgres_cleanup(**values)
    assert values["processes"].calls == []

    technical = tmp_path / "technical"
    technical.mkdir()
    values, _, _, _ = _setup(technical)
    values["processes"] = Processes([_observation(_model(), timed_out=True)])
    with pytest.raises(reconcile.DisposablePostgresCleanupReconcileUnavailable):
        reconcile.reconcile_disposable_postgres_cleanup(**values)


def test_cli_emits_only_canonical_result_or_nothing(monkeypatch, capsys) -> None:
    expected = (
        b'{"operation":"disposable_postgres_runtime_cleanup_reconciliation",'
        b'"outcome":"container_removed","schema_version":1}\n'
    )
    monkeypatch.setattr(reconcile, "reconcile_disposable_postgres_cleanup", lambda **_: expected)
    arguments = [
        "--docker-executable", "/x/docker", "--authorization-file", "/x/auth",
        "--reconciliation-file", "/x/recon", "--claim-reconciliation-file", "/x/claim",
        "--disposition-file", "/x/disposition", "--cleanup-file", "/x/cleanup",
        "--cleanup-reconciliation-file", "/x/current", "--staging-evidence-file", "/x/staging",
        "--compose-file", "/x/compose", "--runtime-env-file", "/x/runtime",
        "--image-env-file", "/x/images", "--project-name", PROJECT,
        "--evidence-directory", "/x/evidence",
    ]
    assert reconcile.main(arguments) == 0
    assert capsys.readouterr().out.encode() == expected
    assert reconcile.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
