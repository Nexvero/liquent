from pathlib import Path


ROOT = Path(__file__).parents[1]
MIGRATION = ROOT / "src/liquent_platform/persistence/alembic/versions/20260825_0035_supervisor_control_directory_cleanup_foundation.py"


def _text() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_revision_is_linear_after_0034() -> None:
    text = _text()
    assert 'revision: str = "20260825_0035"' in text
    assert 'down_revision: str | Sequence[str] | None = "20260825_0034"' in text


def test_exactly_two_empty_foundation_tables_are_created() -> None:
    text = _text()
    assert text.count("op.create_table(") == 2
    assert '"manifest_handoff_supervisor_control_cleanup_decisions"' in text
    assert '"manifest_handoff_supervisor_control_cleanup_attempts"' in text
    for forbidden in ("INSERT", "UPDATE ", "DELETE ", "op.bulk_insert"):
        assert forbidden not in text


def test_decisions_are_sequenced_closed_and_directory_bound() -> None:
    text = _text()
    assert 'sa.PrimaryKeyConstraint(\n            "decision_id"' in text
    assert '"directory_id", "sequence_number"' in text
    assert "sequence_number>0" in text
    assert "disposition IN ('retain','eligible')" in text
    assert "manifest_handoff_supervisor_control_directories.directory_id" in text


def test_attempt_binds_actor_decision_and_same_directory() -> None:
    text = _text()
    assert '["decision_id", "directory_id"]' in text
    assert "manifest_handoff_supervisor_control_cleanup_decisions.decision_id" in text
    assert "manifest_handoff_supervisor_control_cleanup_decisions.directory_id" in text
    assert '["actor_user_id"], ["identity_users.user_id"]' in text


def test_attempt_state_and_value_matrix_is_closed() -> None:
    text = _text()
    assert "state IN ('started','outcome_unknown','completed','reconciled')" in text
    assert "state='started' AND unknown_at IS NULL" in text
    assert "state='outcome_unknown' AND unknown_at IS NOT NULL" in text
    assert "outcome IN ('removed','already_absent')" in text
    assert "reconciliation_outcome IN ('absent','present','conflict')" in text


def test_attempt_times_are_monotone_and_unresolved_is_unique() -> None:
    text = _text()
    assert "unknown_at IS NULL OR unknown_at>=started_at" in text
    assert "completed_at IS NULL OR completed_at>=started_at" in text
    assert "reconciled_at IS NULL OR reconciled_at>=unknown_at" in text
    assert "uq_mh_supervisor_control_cleanup_unresolved_directory" in text
    assert "state IN ('started','outcome_unknown')" in text
    assert "postgresql_where=" in text and "sqlite_where=" in text


def test_no_path_authority_hold_seed_or_cleanup_effect() -> None:
    text = _text()
    for forbidden in (
        "root_path", "leaf", "filename", "inode", "permission", "allow",
        "membership", "legal_hold", "open(", "unlink", "rmdir",
    ):
        assert forbidden not in text


def test_downgrade_is_reverse_scoped_and_preserves_directory_registry() -> None:
    text = _text()
    downgrade = text[text.index("def downgrade") :]
    index = downgrade.index("op.drop_index(")
    attempts = downgrade.index('op.drop_table("manifest_handoff_supervisor_control_cleanup_attempts")')
    decisions = downgrade.index('op.drop_table("manifest_handoff_supervisor_control_cleanup_decisions")')
    assert index < attempts < decisions
    assert 'op.drop_table("manifest_handoff_supervisor_control_directories")' not in downgrade


def test_current_head_bundle_and_roadmap_are_synchronized() -> None:
    gate = (ROOT / "tests/test_persistence_migration_gate.py").read_text(encoding="utf-8")
    bundle = (ROOT / "tools/operational_release_bundle.py").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert 'expected_head() == "20260826_0042"' in gate
    assert "EXPECTED_MIGRATION_COUNT = 42" in bundle
    assert "**42 lineare Migrationen**, Head\n  `20260826_0042`" in roadmap


def test_roadmap_records_lq493_and_lq494() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-493 persistent supervisor control-directory cleanup foundation:" in roadmap
    assert "lq-493-persistent-supervisor-control-directory-cleanup-foundation.md" in roadmap
    assert "nächster Slice LQ-494" in roadmap
