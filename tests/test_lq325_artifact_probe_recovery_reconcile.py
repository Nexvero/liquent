from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from liquent_platform.operators.artifact_probe_recovery_reconcile import (
    reconcile_artifact_probe_claim,
)
from liquent_platform.operators.staging_process_adapter import ProcessObservation
from test_lq312_staging_read_only_probe_cli import APP_IMAGE, NOW, _compose_output, _private, _setup


RECOVERY_ID = "recovery-325"


class Processes:
    def __init__(self, outcome: str): self.outcome, self.calls = outcome, []

    def run(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        if len(self.calls) == 1:
            output = _compose_output()
        else:
            output = json.dumps({
                "schema_version": 1, "inspection": "artifact_probe_recovery",
                "outcome": self.outcome,
            }).encode()
        return ProcessObservation(0, output, b"", False, False, False)


def _inputs(tmp_path: Path):
    docker, authorization, compose, runtime, images = _setup(tmp_path)
    compose_hash = json.loads(authorization.read_text())["compose_sha256"]
    recovery = _private(tmp_path / "recovery.json", json.dumps({
        "schema_version": 1, "recovery_id": RECOVERY_ID, "run_id": "lq312-run",
        "phase": "artifact_capabilities", "source_commit": "a" * 40,
        "image_ref": APP_IMAGE, "compose_sha256": compose_hash,
        "executor_id": "recovery-executor", "authorizer_id": "recovery-authorizer",
        "valid_from": "2026-08-20T13:30:00Z", "valid_until": "2026-08-20T14:30:00Z",
    }))
    reconciliation = _private(tmp_path / "reconciliation.json", json.dumps({
        "schema_version": 1, "reconciliation_id": "reconciliation-325",
        "recovery_id": RECOVERY_ID, "run_id": "lq312-run",
        "phase": "artifact_capabilities", "source_commit": "a" * 40,
        "image_ref": APP_IMAGE, "compose_sha256": compose_hash,
        "recovery_executor_id": "recovery-executor",
        "recovery_authorizer_id": "recovery-authorizer",
        "executor_id": "reconcile-executor", "authorizer_id": "reconcile-authorizer",
        "valid_from": "2026-08-20T13:30:00Z", "valid_until": "2026-08-20T14:30:00Z",
    }))
    evidence = tmp_path / "evidence"
    evidence.mkdir(mode=0o700)
    claim = evidence / f".{hashlib.sha256(RECOVERY_ID.encode()).hexdigest()}.claim"
    claim.write_bytes(b"artifact-probe-recovery\n")
    os.chmod(claim, 0o600)
    return docker, authorization, recovery, reconciliation, compose, runtime, images, evidence, claim


def _run(tmp_path: Path, processes):
    values = _inputs(tmp_path)
    docker, authorization, recovery, reconciliation, compose, runtime, images, evidence, claim = values
    output = reconcile_artifact_probe_claim(
        docker_executable=docker, authorization_file=authorization,
        recovery_file=recovery, reconciliation_file=reconciliation,
        compose_file=compose, runtime_environment_file=runtime,
        image_environment_file=images, project_name="liquent-lq312-run",
        evidence_directory=evidence, processes=processes, clock=lambda: NOW,
    )
    return json.loads(output), evidence, claim


def test_absence_finalizes_evidence_before_removing_claim(tmp_path: Path) -> None:
    processes = Processes("absent")
    result, evidence, claim = _run(tmp_path, processes)
    assert result["outcome"] == "absence_finalized"
    assert not claim.exists() and len(processes.calls) == 2
    records = [json.loads(path.read_text()) for path in evidence.glob("*.json")]
    assert {record["outcome"] for record in records} == {
        "absence_confirmed_after_unknown", "absence_finalized",
    }
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in evidence.glob("*.json"))


def test_recoverable_or_conflict_is_retained_without_write_container(tmp_path: Path) -> None:
    processes = Processes("recoverable")
    result, evidence, claim = _run(tmp_path, processes)
    assert result["outcome"] == "retained" and claim.exists()
    assert len(processes.calls) == 2
    assert all("recovery-remove" not in " ".join(call[0]) for call in processes.calls)
    assert len(list(evidence.glob("reconciliation-*.json"))) == 1


def test_exact_reconciliation_retry_uses_evidence_without_docker(tmp_path: Path) -> None:
    first = Processes("recoverable")
    expected, _, _ = _run(tmp_path, first)
    second = Processes("absent")
    docker, authorization, recovery, reconciliation, compose, runtime, images, evidence, _ = _inputs_existing(tmp_path)
    actual = json.loads(reconcile_artifact_probe_claim(
        docker_executable=docker, authorization_file=authorization,
        recovery_file=recovery, reconciliation_file=reconciliation,
        compose_file=compose, runtime_environment_file=runtime,
        image_environment_file=images, project_name="liquent-lq312-run",
        evidence_directory=evidence, processes=second, clock=lambda: NOW,
    ))
    assert actual == expected and second.calls == []


def test_evidence_first_retry_removes_only_valid_leftover_claims(tmp_path: Path) -> None:
    expected, evidence, recovery_claim = _run(tmp_path, Processes("absent"))
    recovery_claim.write_bytes(b"artifact-probe-recovery\n")
    os.chmod(recovery_claim, 0o600)
    recon_hash = hashlib.sha256(b"reconciliation-325").hexdigest()
    recon_claim = evidence / f".reconciliation-{recon_hash}.claim"
    recon_claim.write_bytes(b"artifact-probe-recovery-reconciliation\n")
    os.chmod(recon_claim, 0o600)
    second = Processes("conflict")
    docker, authorization, recovery, reconciliation, compose, runtime, images, _, _ = _inputs_existing(tmp_path)
    actual = json.loads(reconcile_artifact_probe_claim(
        docker_executable=docker, authorization_file=authorization,
        recovery_file=recovery, reconciliation_file=reconciliation,
        compose_file=compose, runtime_environment_file=runtime,
        image_environment_file=images, project_name="liquent-lq312-run",
        evidence_directory=evidence, processes=second, clock=lambda: NOW,
    ))
    assert actual == expected and second.calls == []
    assert not recovery_claim.exists() and not recon_claim.exists()


def _inputs_existing(tmp_path: Path):
    return (
        tmp_path / "docker", tmp_path / "authorization.json", tmp_path / "recovery.json",
        tmp_path / "reconciliation.json", tmp_path / "compose.yaml",
        tmp_path / "runtime.env", tmp_path / "images.env", tmp_path / "evidence",
        tmp_path / "evidence" / f".{hashlib.sha256(RECOVERY_ID.encode()).hexdigest()}.claim",
    )
