import ast
from pathlib import Path

ROOT=Path(__file__).parents[1]
ADAPTER=ROOT/"src/liquent_platform/persistence/manifest_handoff_supervisor_control_directories.py"
def _text(): return ADAPTER.read_text(encoding="utf-8")
def _methods():
    cls=next(n for n in ast.parse(_text()).body if isinstance(n,ast.ClassDef))
    return {n.name for n in cls.body if isinstance(n,ast.FunctionDef)}

def test_adapter_implements_three_store_and_two_lookup_methods():
    assert {"reserve_control_directory","activate_control_directory","retire_control_directory",
        "resolve_control_directory","resolve_handle_control_directory"} <= _methods()

def test_leaf_is_internal_secure_and_bounded():
    text=_text()
    assert "secrets.token_hex(32)" in text
    assert "for _ in range(4):" in text
    assert "type(leaf) is not ManifestHandoffSupervisorControlDirectoryLeaf" in text

def test_journal_is_checked_before_leaf_and_insert():
    text=_text()
    job=text.index("transaction.execute(_JOB")
    leaf=text.index("leaf = self._available_leaf")
    insert=text.index("INSERT INTO manifest_handoff_supervisor_control_directories")
    assert job < leaf < insert

def test_reservation_retry_reconstructs_original_stage():
    text=_text()
    assert "reservation = self._reservation(row)" in text
    assert "reservation.directory_id == request.directory_id" in text
    assert "reservation.handle_id == request.handle_id" in text

def test_activate_and_retire_are_forward_only_and_idempotent():
    text=_text()
    assert "SET state='active',activated_at=:now" in text
    assert "WHERE directory_id=:directory AND state='reserved'" in text
    assert "SET state='retired',retired_at=:now" in text
    assert "WHERE directory_id=:directory AND state='active'" in text
    assert "type(lifecycle) is ActiveManifestHandoffSupervisorControlDirectory" in text
    assert "type(lifecycle) is RetiredManifestHandoffSupervisorControlDirectory" in text

def test_lookup_queries_once_and_reconstructs_all_states():
    text=_text()
    segment=text[text.index("def _resolve"):text.index("def _available_leaf")]
    assert segment.count("self._one(") == 1
    for state in ("RESERVED","ACTIVE"):
        assert f"ManifestHandoffSupervisorControlDirectoryState.{state}" in text
    assert "RetiredManifestHandoffSupervisorControlDirectory(active" in text

def test_postgres_lock_sqlite_and_detail_free_boundary_exist():
    text=_text()
    assert "LOCK TABLE manifest_handoff_supervisor_journal_jobs" in text
    assert "manifest_handoff_supervisor_control_directories" in text
    assert 'connection.dialect.name == "postgresql"' in text
    assert 'connection.dialect.name != "sqlite"' in text
    assert "ManifestHandoffRegistryUnavailable" in text

def test_no_file_authority_delete_or_wiring():
    text=_text()
    for forbidden in ("Path","os.","open(","mkdir","unlink","SessionPrincipal",
            "UserId","WorkspaceId","Permission","allow","DELETE ","create_app","compose"):
        assert forbidden not in text

def test_roadmap_records_lq487_and_lq488():
    roadmap=(ROOT/"docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-487 persistent supervisor control-directory registry adapter:" in roadmap
    assert "lq-487-persistent-supervisor-control-directory-registry-adapter.md" in roadmap
    assert "nächster Slice LQ-488" in roadmap
