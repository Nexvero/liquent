from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

import liquent_platform.operators.research_worker_staging_evidence as evidence_module
from liquent_platform.operators.research_worker_staging_evidence import (
    CHECKS, main, verify_staging_evidence,
)
from liquent_platform.persistence.migrations import expected_head


NOW = datetime(2026, 8, 19, 12, tzinfo=UTC)


def _record(status: str = "passed") -> dict[str, object]:
    checks = {
        name: {
            "status": status,
            "evidence_ref": None if status == "unavailable" else f"evidence:{index}",
            "evidence_sha256": None if status == "unavailable" else f"{index:064x}",
        }
        for index, name in enumerate(sorted(CHECKS), start=1)
    }
    return {
        "schema_version": 1,
        "run_id": "staging-run-304",
        "environment": "staging",
        "source_commit": "a" * 40,
        "image_ref": "registry.example/liquent@sha256:" + "b" * 64,
        "compose_sha256": "c" * 64,
        "migration_head": expected_head(),
        "observed_at": "2026-08-19T11:00:00Z",
        "review_by": "2026-08-20T11:00:00Z",
        "prepared_by": "operator-304",
        "reviewed_by": "reviewer-304",
        "checks": checks,
    }


def _private(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def _verify(path: Path) -> str:
    return verify_staging_evidence(path, clock=lambda: NOW)


def test_complete_current_independently_reviewed_evidence_approves(tmp_path: Path) -> None:
    assert _verify(_private(tmp_path / "evidence.json", _record())) == "approved"


def test_failed_check_rejects_and_unavailable_check_is_unavailable(tmp_path: Path) -> None:
    failed = _record()
    failed["checks"]["running_sigterm"] = {
        "status": "failed", "evidence_ref": "evidence:failed",
        "evidence_sha256": "d" * 64,
    }
    assert _verify(_private(tmp_path / "failed.json", failed)) == "rejected"
    unavailable = _record()
    unavailable["checks"]["migration_gate"] = {
        "status": "unavailable", "evidence_ref": None, "evidence_sha256": None,
    }
    assert _verify(_private(tmp_path / "unavailable.json", unavailable)) == "unavailable"


@pytest.mark.parametrize("mutation", [
    lambda value: value.update(environment="production"),
    lambda value: value.update(image_ref="liquent:latest"),
    lambda value: value.update(migration_head="old-head"),
    lambda value: value.update(reviewed_by=value["prepared_by"]),
    lambda value: value.update(observed_at="2026-08-20T12:00:00Z"),
    lambda value: value.update(review_by="2026-08-19T11:59:59Z"),
    lambda value: value["checks"].pop("idle_sigterm"),
    lambda value: value.update(extra="not-closed"),
])
def test_binding_structure_identity_and_time_fail_closed(tmp_path: Path, mutation) -> None:
    value = _record()
    mutation(value)
    assert _verify(_private(tmp_path / "evidence.json", value)) == "unavailable"


@pytest.mark.parametrize("private_value", [
    "postgresql+psycopg://user:secret@db/staging",
    "https://private.example/evidence",
    "/run/secrets/database_url",
    "/Users/operator/private/evidence",
    "-----BEGIN PRIVATE KEY-----",
])
def test_private_or_network_material_is_never_accepted(
    tmp_path: Path, private_value: str,
) -> None:
    value = _record()
    value["run_id"] = private_value
    assert _verify(_private(tmp_path / "evidence.json", value)) == "unavailable"


def test_duplicate_json_keys_wrong_permissions_and_symlink_are_unavailable(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"schema_version":1,"schema_version":1}\n')
    os.chmod(duplicate, 0o600)
    assert _verify(duplicate) == "unavailable"
    broad = _private(tmp_path / "broad.json", _record())
    os.chmod(broad, 0o644)
    assert _verify(broad) == "unavailable"
    target = _private(tmp_path / "target.json", _record())
    link = tmp_path / "link.json"
    link.symlink_to(target)
    assert _verify(link) == "unavailable"


def test_cli_prints_only_decision_and_uses_stable_exit_codes(
    tmp_path: Path, capsys, monkeypatch,
) -> None:
    monkeypatch.setattr(
        evidence_module, "verify_staging_evidence",
        lambda path: verify_staging_evidence(path, clock=lambda: NOW),
    )
    approved = _private(tmp_path / "approved.json", _record())
    assert main(["--evidence", str(approved)]) == 0
    assert capsys.readouterr().out == "approved\n"
    missing = tmp_path / "private-missing-name.json"
    assert main(["--evidence", str(missing)]) == 2
    captured = capsys.readouterr()
    assert captured.out == "unavailable\n" and captured.err == ""
