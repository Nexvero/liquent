from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.operators import (
    manifest_handoff_supervisor_control_directory_cleanup as operator,
)


pytestmark = pytest.mark.postgres_integration


def _private(path: Path, value: str) -> Path:
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)
    return path


def _b(value: str) -> bytes:
    return value.encode("utf-8")


def _seed_complete_retired_writer(
    engine: Engine, root: Path
) -> tuple[str, str, str]:
    actor = "lq520-actor"
    scope = "lq520-scope"
    backend = "lq520-backend"
    handle = "lq520-handle"
    directory = "lq520-directory"
    leaf = "a" * 64
    handoff_attempt = "lq520-handoff-attempt"
    execution_claim = "lq520-execution-claim"
    prepare = "lq520-prepare"
    terminal = "lq520-terminal"
    now = datetime.now(timezone.utc) - timedelta(days=1)
    leaf_path = root / leaf
    leaf_path.mkdir(mode=0o700)

    values = {
        "actor": _b(actor), "scope": _b(scope), "backend": _b(backend),
        "handle": _b(handle), "directory": _b(directory), "leaf": leaf,
        "attempt": _b(handoff_attempt), "reservation": _b("lq520-reservation"),
        "claim": _b(execution_claim), "owner": _b("lq520-owner"),
        "prepare": _b(prepare), "launch": _b("lq520-launch"),
        "terminal": _b(terminal), "decision": _b("lq520-decision"),
        "management": _b("lq520-management"), "hold": _b("lq520-hold"),
        "recovery": _b("lq520-recovery"), "reference": _b("lq520-reference"),
        "t0": now, "t1": now + timedelta(seconds=1),
        "t2": now + timedelta(seconds=2), "t3": now + timedelta(seconds=3),
        "t4": now + timedelta(seconds=4),
        "source": str(root / "source"), "target": str(root / "target"),
    }
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO identity_users (user_id,status) VALUES (:actor,'active')"
        ), values)
        connection.execute(text(
            "INSERT INTO manifest_handoff_registry_scopes (scope_id,status)"
            " VALUES (:scope,'active')"
        ), values)
        connection.execute(text(
            "INSERT INTO manifest_handoff_attempts"
            " (attempt_id,reservation_id,scope_id,actor_user_id,handoff_name,reserved_at)"
            " VALUES (:attempt,:reservation,:scope,:actor,'lq520-handoff',:t0)"
        ), values)
        connection.execute(text(
            "INSERT INTO manifest_handoff_execution_claims"
            " (claim_id,attempt_id,actor_user_id,owner_id,claimed_at,lease_expires_at)"
            " VALUES (:claim,:attempt,:actor,:owner,:t0,:t4)"
        ), values)
        connection.execute(text(
            "INSERT INTO manifest_handoff_supervisor_backends"
            " (backend_instance_id,status,provisioned_at) VALUES (:backend,'active',:t0)"
        ), values)
        connection.execute(text(
            "INSERT INTO manifest_handoff_supervisor_preparations"
            " (prepare_id,backend_instance_id,capability,execution_claim_id,"
            " recovery_claim_id,owner_id,reserved_at)"
            " VALUES (:prepare,:backend,'writer',:claim,NULL,:owner,:t0)"
        ), values)
        connection.execute(text(
            "INSERT INTO manifest_handoff_supervisor_handle_bindings"
            " (handle_id,prepare_id,backend_instance_id,bound_at)"
            " VALUES (:handle,:prepare,:backend,:t0)"
        ), values)
        connection.execute(text(
            "INSERT INTO manifest_handoff_supervisor_terminal_observations"
            " (terminal_observation_id,handle_id,observed_at)"
            " VALUES (:terminal,:handle,:t3)"
        ), values)
        connection.execute(text(
            "INSERT INTO manifest_handoff_supervisor_journal_jobs"
            " (handle_id,backend_instance_id,prepare_id,launch_commit_id,capability,"
            " execution_claim_id,recovery_claim_id,owner_id,scope_id,source_root,"
            " target_root,handoff_name,registered_at) VALUES"
            " (:handle,:backend,:prepare,:launch,'writer',:claim,NULL,:owner,:scope,"
            " :source,:target,'lq520-handoff',:t0)"
        ), values)
        connection.execute(text(
            "INSERT INTO manifest_handoff_supervisor_journal_transitions"
            " (transition_id,handle_id,capability,sequence_number,kind,outcome_kind,"
            " filename,manifest_sha256,file_count,observed_at) VALUES"
            " (:launch,:handle,'writer',1,'launch_committed',NULL,NULL,NULL,NULL,:t1),"
            " (:terminal,:handle,'writer',2,'terminal_observed','unavailable',"
            " NULL,NULL,NULL,:t3)"
        ), values)
        connection.execute(text(
            "INSERT INTO manifest_handoff_supervisor_control_directories"
            " (directory_id,handle_id,leaf,state,reserved_at,activated_at,retired_at)"
            " VALUES (:directory,:handle,:leaf,'retired',:t0,:t1,:t2)"
        ), values)
        connection.execute(text(
            "INSERT INTO manifest_handoff_supervisor_control_cleanup_decisions"
            " (decision_id,directory_id,sequence_number,policy_revision_id,"
            " disposition,decided_at) VALUES"
            " (:decision,:directory,1,'lq520-policy','eligible',:t4)"
        ), values)
        connection.execute(text(
            "INSERT INTO mh_supervisor_cleanup_retention_policy_revisions"
            " (revision_id,data_class,minimum_retention_seconds,created_at)"
            " VALUES ('lq520-policy','supervisor_control_directory',1,:t4)"
        ), values)
        connection.execute(text(
            "INSERT INTO mh_supervisor_cleanup_retention_policy_active"
            " (data_class,revision_id,activated_at) VALUES"
            " ('supervisor_control_directory','lq520-policy',:t4)"
        ), values)
        connection.execute(text(
            "INSERT INTO manifest_handoff_supervisor_cleanup_management_revisions"
            " (revision_id,actor_user_id,scope_id,sequence_number,status,resolved_at)"
            " VALUES (:management,:actor,:scope,1,'active',:t4)"
        ), values)
        for kind in ("hold", "recovery", "reference"):
            connection.execute(text(
                f"INSERT INTO manifest_handoff_supervisor_cleanup_{kind}_revisions"
                " (revision_id,directory_id,sequence_number,disposition,decided_at)"
                f" VALUES (:{kind},:directory,1,'clear',:t4)"
            ), values)
    return actor, backend, directory


def _arguments(tmp_path: Path, postgres_url: str, backend: str, root: Path,
               command: str, request: dict[str, str]) -> list[str]:
    database = _private(tmp_path / f"{command}-database", postgres_url + "\n")
    backend_file = _private(tmp_path / f"{command}-backend", backend + "\n")
    root_file = _private(tmp_path / f"{command}-root", str(root) + "\n")
    request_file = _private(
        tmp_path / f"{command}-request.json",
        json.dumps(request, sort_keys=True, separators=(",", ":")) + "\n",
    )
    return [
        command,
        "--database-url-file", str(database),
        "--backend-instance-id-file", str(backend_file),
        "--control-root-file", str(root_file),
        "--request", str(request_file),
    ]


def test_execute_removes_once_and_terminal_attempt_cannot_be_reconciled(
    postgres_engine: Engine, postgres_url: str, tmp_path: Path, capsys
) -> None:
    root = tmp_path / "control"
    root.mkdir(mode=0o700)
    actor, backend, directory = _seed_complete_retired_writer(postgres_engine, root)

    execute = _arguments(
        tmp_path, postgres_url, backend, root, "execute",
        {"actor_user_id": actor, "directory_id": directory},
    )
    assert operator.main(execute) == 0
    executed = json.loads(capsys.readouterr().out)
    assert executed["outcome"] == "removed"
    assert executed["directory_id"] == directory
    assert set(executed) == {"attempt_id", "directory_id", "outcome"}
    assert list(root.iterdir()) == []

    with postgres_engine.connect() as connection:
        attempt = connection.execute(text(
            "SELECT state,outcome,completed_at FROM"
            " manifest_handoff_supervisor_control_cleanup_attempts"
            " WHERE attempt_id=:attempt"
        ), {"attempt": _b(executed["attempt_id"])}).one()
        claims = connection.scalar(text(
            "SELECT count(*) FROM"
            " manifest_handoff_supervisor_control_cleanup_write_claims"
        ))
    assert attempt.state == "completed"
    assert attempt.outcome == "removed"
    assert attempt.completed_at is not None
    assert claims == 1

    reconcile = _arguments(
        tmp_path, postgres_url, backend, root, "reconcile",
        {"attempt_id": executed["attempt_id"], "directory_id": directory},
    )
    assert operator.main(reconcile) == 0
    reconciled = json.loads(capsys.readouterr().out)
    assert reconciled == {
        "attempt_id": executed["attempt_id"],
        "directory_id": directory,
        "outcome": "rejected",
    }

    with postgres_engine.connect() as connection:
        unchanged = connection.execute(text(
            "SELECT state,outcome,reconciliation_outcome FROM"
            " manifest_handoff_supervisor_control_cleanup_attempts"
            " WHERE attempt_id=:attempt"
        ), {"attempt": _b(executed["attempt_id"])}).one()
        claim_count = connection.scalar(text(
            "SELECT count(*) FROM"
            " manifest_handoff_supervisor_control_cleanup_write_claims"
        ))
    assert unchanged == ("completed", "removed", None)
    assert claim_count == 1
    assert list(root.iterdir()) == []
