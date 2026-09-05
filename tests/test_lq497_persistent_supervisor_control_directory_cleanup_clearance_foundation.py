from pathlib import Path


ROOT = Path(__file__).parents[1]
MIGRATION = ROOT / "src/liquent_platform/persistence/alembic/versions/20260825_0036_supervisor_control_directory_cleanup_clearance_foundation.py"


def _text() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_revision_is_linear_after_0035() -> None:
    text = _text()
    assert 'revision: str = "20260825_0036"' in text
    assert 'down_revision: str | Sequence[str] | None = "20260825_0035"' in text


def test_five_empty_tables_are_created_without_seed_or_backfill() -> None:
    text = _text()
    assert text.count("op.create_table(") == 3
    assert '_target_revision_table("hold")' in text
    assert '_target_revision_table("recovery")' in text
    assert '_target_revision_table("reference")' in text
    assert '"manifest_handoff_supervisor_cleanup_management_revisions"' in text
    assert '"manifest_handoff_supervisor_cleanup_clearances"' in text
    for forbidden in ("INSERT", "UPDATE ", "DELETE ", "op.bulk_insert"):
        assert forbidden not in text


def test_management_is_actor_scope_sequenced_and_closed() -> None:
    text = _text()
    assert '"actor_user_id", "scope_id", "sequence_number"' in text
    assert "sequence_number>0" in text
    assert "status IN ('active','inactive')" in text
    assert '["actor_user_id"], ["identity_users.user_id"]' in text
    assert '["scope_id"], ["manifest_handoff_registry_scopes.scope_id"]' in text


def test_target_sources_are_separate_directory_bound_and_closed() -> None:
    text = _text()
    assert 'table = f"manifest_handoff_supervisor_cleanup_{kind}_revisions"' in text
    assert '"directory_id", "sequence_number"' in text
    assert "manifest_handoff_supervisor_control_directories.directory_id" in text
    assert "disposition IN ('clear','blocked')" in text


def test_clearance_is_unique_per_attempt_and_binds_retention_target() -> None:
    text = _text()
    assert 'sa.UniqueConstraint(\n            "attempt_id"' in text
    assert "manifest_handoff_supervisor_control_cleanup_attempts.attempt_id" in text
    assert '["decision_id", "directory_id"]' in text
    assert "manifest_handoff_supervisor_control_cleanup_decisions.decision_id" in text


def test_clearance_binds_management_actor_scope_and_three_target_revisions() -> None:
    text = _text()
    assert '["management_revision_id", "actor_user_id", "scope_id"]' in text
    for kind in ("hold", "recovery", "reference"):
        assert f'["{kind}_revision_id", "directory_id"]' in text
        assert f"manifest_handoff_supervisor_cleanup_{kind}_revisions.revision_id" in text


def test_clearance_binds_persistent_terminal_observation() -> None:
    text = _text()
    assert '["terminal_observation_id"]' in text
    assert "manifest_handoff_supervisor_terminal_observations.terminal_observation_id" in text


def test_no_path_allow_outcome_seed_or_file_effect() -> None:
    text = _text()
    for forbidden in (
        "root_path", "leaf", "filename", "inode", "permission", "allow",
        "payload", "outcome", "open(", "unlink", "rmdir",
    ):
        assert forbidden not in text


def test_downgrade_is_reverse_scoped() -> None:
    text = _text()
    section = text[text.index("def downgrade") :]
    order = [
        "cleanup_clearances", "cleanup_reference_revisions",
        "cleanup_recovery_revisions", "cleanup_hold_revisions",
        "cleanup_management_revisions",
    ]
    positions = [section.index(value) for value in order]
    assert positions == sorted(positions)
    assert "control_cleanup_attempts" not in section


def test_current_head_bundle_and_roadmap_are_synchronized() -> None:
    gate = (ROOT / "tests/test_persistence_migration_gate.py").read_text(encoding="utf-8")
    bundle = (ROOT / "tools/operational_release_bundle.py").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert 'expected_head() == "20260826_0042"' in gate
    assert "EXPECTED_MIGRATION_COUNT = 42" in bundle
    assert "**42 lineare Migrationen**, Head\n  `20260826_0042`" in roadmap


def test_roadmap_records_lq497_and_lq498() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-497 persistent supervisor control-directory cleanup clearance foundation:" in roadmap
    assert "lq-497-persistent-supervisor-control-directory-cleanup-clearance-foundation.md" in roadmap
    assert "nächster Slice LQ-498" in roadmap
