from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorBackendInstanceId,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlDirectoryId,
)
from liquent_platform.operators.manifest_handoff_supervisor_control_directory_retirement import (
    execute_one,
)


pytestmark = pytest.mark.postgres_integration
NOW = datetime(2020, 8, 28, tzinfo=timezone.utc)


def _seed(engine: Engine, name: str, *, terminal: bool) -> tuple[
    ManifestHandoffSupervisorBackendInstanceId,
    ManifestHandoffSupervisorControlDirectoryId,
]:
    backend = ManifestHandoffSupervisorBackendInstanceId(f"{name}-backend")
    directory = ManifestHandoffSupervisorControlDirectoryId(f"{name}-directory")
    values = {
        "handle": f"{name}-handle".encode(),
        "backend": backend.value.encode(),
        "prepare": f"{name}-prepare".encode(),
        "launch": f"{name}-launch".encode(),
        "claim": f"{name}-claim".encode(),
        "owner": f"{name}-owner".encode(),
        "scope": f"{name}-scope".encode(),
        "terminal": f"{name}-terminal".encode(),
        "directory": directory.value.encode(),
        "leaf": ("d" if terminal else "e") * 64,
        "t0": NOW,
        "t1": NOW + timedelta(seconds=1),
        "t2": NOW + timedelta(seconds=2),
    }
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO manifest_handoff_supervisor_journal_jobs "
            "(handle_id,backend_instance_id,prepare_id,launch_commit_id,capability,"
            "execution_claim_id,recovery_claim_id,owner_id,scope_id,source_root,"
            "target_root,handoff_name,registered_at) VALUES "
            "(:handle,:backend,:prepare,:launch,'writer',:claim,NULL,:owner,:scope,"
            "'/source','/target',:name,:t0)"
        ), {**values, "name": name})
        if terminal:
            connection.execute(text(
                "INSERT INTO manifest_handoff_supervisor_journal_transitions "
                "(transition_id,handle_id,capability,sequence_number,kind,outcome_kind,"
                "filename,manifest_sha256,file_count,observed_at) VALUES "
                "(:launch,:handle,'writer',1,'launch_committed',NULL,NULL,NULL,NULL,:t1),"
                "(:terminal,:handle,'writer',2,'terminal_observed','unavailable',"
                "NULL,NULL,NULL,:t2)"
            ), values)
        connection.execute(text(
            "INSERT INTO manifest_handoff_supervisor_control_directories "
            "(directory_id,handle_id,leaf,state,reserved_at,activated_at,retired_at) "
            "VALUES (:directory,:handle,:leaf,'active',:t0,:t1,NULL)"
        ), values)
    return backend, directory


def test_postgresql_terminal_retirement_and_retry_are_stable(
    postgres_engine: Engine,
) -> None:
    backend, directory = _seed(postgres_engine, "lq587-terminal", terminal=True)

    first = execute_one(postgres_engine, backend, directory)
    second = execute_one(postgres_engine, backend, directory)

    assert first == second
    assert first["directory_id"] == directory.value
    assert first["handle_id"] == "lq587-terminal-handle"
    retired_at = datetime.fromisoformat(first["retired_at"].replace("Z", "+00:00"))
    assert retired_at > NOW
    with postgres_engine.connect() as connection:
        row = connection.execute(text(
            "SELECT state,retired_at FROM "
            "manifest_handoff_supervisor_control_directories "
            "WHERE directory_id=:directory"
        ), {"directory": directory.value.encode()}).one()
    assert row.state == "retired"
    assert row.retired_at == retired_at


def test_postgresql_nonterminal_and_unknown_remain_effect_free(
    postgres_engine: Engine,
) -> None:
    backend, directory = _seed(postgres_engine, "lq587-open", terminal=False)

    assert execute_one(postgres_engine, backend, directory) is None
    assert execute_one(
        postgres_engine,
        backend,
        ManifestHandoffSupervisorControlDirectoryId("lq587-unknown"),
    ) is None
    with postgres_engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT state FROM manifest_handoff_supervisor_control_directories "
            "WHERE directory_id=:directory"
        ), {"directory": directory.value.encode()}) == "active"
