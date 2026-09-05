from pathlib import Path

ROOT=Path(__file__).parents[1]
MIGRATION=ROOT/"src/liquent_platform/persistence/alembic/versions/20260825_0034_supervisor_control_directory_registry.py"
def _text(): return MIGRATION.read_text(encoding="utf-8")

def test_revision_is_linear_after_0033():
    text=_text()
    assert 'revision: str = "20260825_0034"' in text
    assert 'down_revision: str | Sequence[str] | None = "20260825_0033"' in text

def test_one_control_directory_registry_table_is_created():
    text=_text()
    assert text.count("op.create_table(") == 1
    assert '"manifest_handoff_supervisor_control_directories"' in text
    assert text.count("op.drop_table(") == 1

def test_directory_handle_and_leaf_are_nonreusable():
    text=_text()
    assert 'sa.PrimaryKeyConstraint("directory_id"' in text
    assert 'sa.UniqueConstraint("handle_id"' in text
    assert 'sa.UniqueConstraint("leaf"' in text
    assert '"manifest_handoff_supervisor_journal_jobs.handle_id"' in text

def test_leaf_and_state_are_closed():
    text=_text()
    assert "length(leaf)=64 AND leaf=lower(leaf)" in text
    assert "state IN ('reserved','active','retired')" in text

def test_state_time_matrix_and_order_are_constrained():
    text=_text()
    assert "state='reserved' AND activated_at IS NULL AND retired_at IS NULL" in text
    assert "state='active' AND activated_at IS NOT NULL AND retired_at IS NULL" in text
    assert "state='retired' AND activated_at IS NOT NULL AND retired_at IS NOT NULL" in text
    assert "activated_at IS NULL OR activated_at>=reserved_at" in text
    assert "retired_at IS NULL OR retired_at>=activated_at" in text

def test_no_path_authority_seed_or_delete_semantics():
    text=_text()
    for forbidden in ("root_path","absolute_path","relative_path","user_id",
            "workspace_id","permission","allow","INSERT INTO","UPDATE ","DELETE "):
        assert forbidden not in text

def test_current_head_bundle_and_roadmap_are_synchronized():
    gate=(ROOT/"tests/test_persistence_migration_gate.py").read_text(encoding="utf-8")
    bundle=(ROOT/"tools/operational_release_bundle.py").read_text(encoding="utf-8")
    roadmap=(ROOT/"docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert 'expected_head() == "20260826_0042"' in gate
    assert "EXPECTED_MIGRATION_COUNT = 42" in bundle
    assert "**42 lineare Migrationen**, Head\n  `20260826_0042`" in roadmap

def test_roadmap_records_lq486_and_lq487():
    roadmap=(ROOT/"docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-486 persistent supervisor control-directory registry foundation:" in roadmap
    assert "lq-486-persistent-supervisor-control-directory-registry-foundation.md" in roadmap
    assert "nächster Slice LQ-487" in roadmap
