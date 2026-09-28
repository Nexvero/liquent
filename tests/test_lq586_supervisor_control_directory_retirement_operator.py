from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from sqlalchemy import Engine, text

from liquent_platform.identity.manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorBackendInstanceId,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlDirectoryId,
)
from liquent_platform.operators.manifest_handoff_supervisor_control_directory_retirement import (
    execute_one,
    main,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head


BACKEND = ManifestHandoffSupervisorBackendInstanceId("lq586-backend")
DIRECTORY = ManifestHandoffSupervisorControlDirectoryId("lq586-directory")
NOW = datetime(2020, 8, 28, tzinfo=timezone.utc)


def _seed(engine: Engine, *, terminal: bool = True, reserved: bool = False) -> None:
    values = {
        "handle": b"lq586-handle",
        "backend": BACKEND.value.encode(),
        "prepare": b"lq586-prepare",
        "launch": b"lq586-launch",
        "claim": b"lq586-claim",
        "owner": b"lq586-owner",
        "scope": b"lq586-scope",
        "terminal": b"lq586-terminal",
        "directory": DIRECTORY.value.encode(),
        "leaf": "c" * 64,
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
            "'/source','/target','lq586',:t0)"
        ), values)
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
            "VALUES (:directory,:handle,:leaf,:state,:t0,:activated,NULL)"
        ), {
            **values,
            "state": "reserved" if reserved else "active",
            "activated": None if reserved else NOW + timedelta(seconds=1),
        })


def _engine(tmp_path: Path) -> tuple[str, Engine]:
    url = f"sqlite:///{tmp_path / 'retirement.db'}"
    upgrade_to_head(url)
    return url, build_engine(url)


def test_execute_retires_terminal_active_directory_and_retry_is_stable(
    tmp_path: Path,
) -> None:
    _url, engine = _engine(tmp_path)
    try:
        _seed(engine)
        first = execute_one(engine, BACKEND, DIRECTORY)
        second = execute_one(engine, BACKEND, DIRECTORY)
        assert first == second
        assert first["directory_id"] == DIRECTORY.value
        assert first["handle_id"] == "lq586-handle"
        retired_at = datetime.fromisoformat(first["retired_at"].replace("Z", "+00:00"))
        assert retired_at > NOW
        with engine.connect() as connection:
            row = connection.execute(text(
                "SELECT state,retired_at FROM "
                "manifest_handoff_supervisor_control_directories"
            )).one()
        assert row.state == "retired"
        assert datetime.fromisoformat(row.retired_at) == retired_at
    finally:
        engine.dispose()


def test_unknown_reserved_and_nonterminal_are_rejected_without_mutation(
    tmp_path: Path,
) -> None:
    url, engine = _engine(tmp_path)
    try:
        assert execute_one(engine, BACKEND, DIRECTORY) is None
        _seed(engine, terminal=False, reserved=True)
        assert execute_one(engine, BACKEND, DIRECTORY) is None
        with engine.connect() as connection:
            assert connection.scalar(text(
                "SELECT state FROM manifest_handoff_supervisor_control_directories"
            )) == "reserved"
    finally:
        engine.dispose()

    other = build_engine(url)
    try:
        with other.begin() as connection:
            connection.execute(text(
                "UPDATE manifest_handoff_supervisor_control_directories "
                "SET state='active',activated_at=:time WHERE directory_id=:directory"
            ), {"time": NOW + timedelta(seconds=1), "directory": DIRECTORY.value.encode()})
        assert execute_one(other, BACKEND, DIRECTORY) is None
        with other.connect() as connection:
            assert connection.scalar(text(
                "SELECT state FROM manifest_handoff_supervisor_control_directories"
            )) == "active"
    finally:
        other.dispose()


def test_cli_writes_private_atomic_result_and_emits_closed_outcome(
    tmp_path: Path, capsys,
) -> None:
    tmp_path.chmod(0o700)
    url, engine = _engine(tmp_path)
    try:
        _seed(engine)
    finally:
        engine.dispose()
    database_file = tmp_path / "database-url"
    backend_file = tmp_path / "backend-id"
    request_file = tmp_path / "request.json"
    result_file = tmp_path / "result.json"
    database_file.write_text(url)
    backend_file.write_text(BACKEND.value)
    request_file.write_text(json.dumps({"directory_id": DIRECTORY.value}))
    for path in (database_file, backend_file, request_file):
        path.chmod(0o600)

    assert main([
        "--database-url-file", str(database_file),
        "--backend-instance-id-file", str(backend_file),
        "--request", str(request_file),
        "--result-file", str(result_file),
    ]) == 0
    assert capsys.readouterr().out == '{"outcome":"applied"}\n'
    payload = json.loads(result_file.read_text())
    assert payload["directory_id"] == DIRECTORY.value
    assert payload["handle_id"] == "lq586-handle"
    assert datetime.fromisoformat(payload["retired_at"].replace("Z", "+00:00")) > NOW
    assert result_file.stat().st_mode & 0o077 == 0


def test_cli_rejects_unknown_without_result_file(tmp_path: Path, capsys) -> None:
    tmp_path.chmod(0o700)
    url, engine = _engine(tmp_path)
    engine.dispose()
    database_file = tmp_path / "database-url"
    backend_file = tmp_path / "backend-id"
    request_file = tmp_path / "request.json"
    result_file = tmp_path / "result.json"
    database_file.write_text(url)
    backend_file.write_text(BACKEND.value)
    request_file.write_text(json.dumps({"directory_id": "unknown"}))
    for path in (database_file, backend_file, request_file):
        path.chmod(0o600)

    assert main([
        "--database-url-file", str(database_file),
        "--backend-instance-id-file", str(backend_file),
        "--request", str(request_file),
        "--result-file", str(result_file),
    ]) == 1
    assert capsys.readouterr().out == '{"outcome":"rejected"}\n'
    assert not result_file.exists()
