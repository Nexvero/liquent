from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import stat

import pytest
from sqlalchemy import Engine, text

from liquent_platform.operators import (
    manifest_handoff_supervisor_control_directory_cleanup as operator,
)
from test_lq520_supervisor_control_directory_cleanup_operator_postgres import (
    _arguments,
    _b,
    _seed_complete_retired_writer,
)


pytestmark = pytest.mark.postgres_integration
_LEAF = "a" * 64


def _seed_claimed_cleanup(engine: Engine, actor: str, directory: str,
                          case: str) -> str:
    attempt = f"lq521-{case}-attempt"
    now = datetime.now(timezone.utc) - timedelta(hours=1)
    values = {
        "attempt": _b(attempt), "directory": _b(directory), "actor": _b(actor),
        "decision": _b("lq520-decision"), "clearance": _b(f"lq521-{case}-clearance"),
        "claim": _b(f"lq521-{case}-claim"), "preflight": _b(f"lq521-{case}-preflight"),
        "scope": _b("lq520-scope"), "terminal": _b("lq520-terminal"),
        "management": _b("lq520-management"), "hold": _b("lq520-hold"),
        "recovery": _b("lq520-recovery"), "reference": _b("lq520-reference"),
        "started": now, "cleared": now + timedelta(seconds=1),
        "prepared": now + timedelta(seconds=2),
        "claimed": now + timedelta(seconds=3),
    }
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO manifest_handoff_supervisor_control_cleanup_attempts"
            " (attempt_id,directory_id,actor_user_id,decision_id,state,started_at,"
            " unknown_at,outcome,completed_at,reconciliation_outcome,reconciled_at,"
            " write_claimed_at) VALUES"
            " (:attempt,:directory,:actor,:decision,'write_claimed',:started,"
            " NULL,NULL,NULL,NULL,NULL,:claimed)"
        ), values)
        connection.execute(text(
            "INSERT INTO manifest_handoff_supervisor_cleanup_clearances"
            " (clearance_id,attempt_id,directory_id,actor_user_id,scope_id,"
            " terminal_observation_id,decision_id,management_revision_id,"
            " hold_revision_id,recovery_revision_id,reference_revision_id,cleared_at)"
            " VALUES (:clearance,:attempt,:directory,:actor,:scope,:terminal,:decision,"
            " :management,:hold,:recovery,:reference,:cleared)"
        ), values)
        connection.execute(text(
            "INSERT INTO manifest_handoff_supervisor_control_cleanup_write_claims"
            " (claim_id,attempt_id,directory_id,clearance_id,preflight_id,"
            " prepared_at,claimed_at) VALUES"
            " (:claim,:attempt,:directory,:clearance,:preflight,:prepared,:claimed)"
        ), values)
    return attempt


def _physical_snapshot(root: Path):
    leaf = root / _LEAF
    if not leaf.exists():
        return ("absent",)
    names = tuple(sorted(path.name for path in leaf.iterdir()))
    values = []
    for name in names:
        path = leaf / name
        values.append((name, path.read_bytes(), stat.S_IMODE(path.stat().st_mode)))
    return ("present", stat.S_IMODE(leaf.stat().st_mode), tuple(values))


@pytest.mark.parametrize("case", ("absent", "present", "conflict"))
def test_real_operator_reconciles_claimed_crash_state_read_only(
    case: str, postgres_engine: Engine, postgres_url: str,
    tmp_path: Path, capsys,
) -> None:
    root = tmp_path / "control"
    root.mkdir(mode=0o700)
    actor, backend, directory = _seed_complete_retired_writer(postgres_engine, root)
    attempt = _seed_claimed_cleanup(postgres_engine, actor, directory, case)
    leaf = root / _LEAF
    if case == "absent":
        leaf.rmdir()
    elif case == "conflict":
        unexpected = leaf / "unexpected"
        unexpected.write_bytes(b"lq521-conflict")
        unexpected.chmod(0o600)
    before = _physical_snapshot(root)

    arguments = _arguments(
        tmp_path, postgres_url, backend, root, "reconcile",
        {"attempt_id": attempt, "directory_id": directory},
    )
    assert operator.main(arguments) == 0
    result = json.loads(capsys.readouterr().out)
    assert result == {
        "attempt_id": attempt,
        "directory_id": directory,
        "outcome": case,
    }
    assert _physical_snapshot(root) == before

    with postgres_engine.connect() as connection:
        persisted = connection.execute(text(
            "SELECT state,unknown_at,outcome,completed_at,reconciliation_outcome,"
            " reconciled_at,write_claimed_at FROM"
            " manifest_handoff_supervisor_control_cleanup_attempts"
            " WHERE attempt_id=:attempt"
        ), {"attempt": _b(attempt)}).one()
        claims = connection.scalar(text(
            "SELECT count(*) FROM"
            " manifest_handoff_supervisor_control_cleanup_write_claims"
            " WHERE attempt_id=:attempt"
        ), {"attempt": _b(attempt)})
    assert persisted.state == "reconciled"
    assert persisted.unknown_at is not None
    assert persisted.outcome is None
    assert persisted.completed_at is None
    assert persisted.reconciliation_outcome == case
    assert persisted.reconciled_at is not None
    assert persisted.reconciled_at >= persisted.unknown_at >= persisted.write_claimed_at
    assert claims == 1
