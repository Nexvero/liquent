from pathlib import Path


ROOT = Path(__file__).parents[1]
MIGRATION = ROOT / "src/liquent_platform/persistence/alembic/versions/20260826_0042_cleanup_retention_policy_foundation.py"


def _text() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_migration_is_linear_empty_nine_table_foundation() -> None:
    text = _text()
    assert 'revision: str = "20260826_0042"' in text
    assert 'down_revision: str | Sequence[str] | None = "20260826_0041"' in text
    assert text.count("op.create_table(") == 9
    assert not any(word in text.lower() for word in ("op.execute", "insert(", "update(", "delete("))


def test_policy_revision_and_single_active_projection_are_bound() -> None:
    text = _text()
    assert 'minimum_retention_seconds>0' in text
    assert "data_class='supervisor_control_directory'" in text
    assert 'sa.PrimaryKeyConstraint(\n            "data_class", name="pk_mh_supervisor_cleanup_retention_policy_active"' in text
    assert "fk_mh_supervisor_cleanup_retention_policy_active_revision" in text


def test_policy_change_matrix_is_closed_and_actor_bound() -> None:
    text = _text()
    assert "fk_mh_supervisor_cleanup_retention_policy_change_actor" in text
    assert "intent='replace' AND result_revision_id IS NOT NULL" in text
    assert "intent='deactivate' AND expected_revision_id IS NOT NULL" in text
    assert "result_revision_id IS NULL AND minimum_retention_seconds IS NULL" in text


def test_complete_authority_history_and_current_pointer_are_bound() -> None:
    text = _text()
    assert "uq_mh_supervisor_cleanup_retention_authority_sequence" in text
    assert "fk_mh_supervisor_cleanup_retention_authority_member_user" in text
    assert "status IN ('active','inactive')" in text
    assert "pk_mh_supervisor_cleanup_retention_authority_current" in text
    assert "fk_mh_supervisor_cleanup_retention_authority_current_set" in text


def test_authority_changes_bind_actor_target_expected_and_result() -> None:
    text = _text()
    for fragment in (
        "authority_change_actor", "authority_change_target",
        "authority_change_expected", "authority_change_result",
        "intent IN ('grant','deactivate','reactivate')",
    ):
        assert fragment in text


def test_bootstrap_binds_both_initial_sides_and_positive_duration() -> None:
    text = _text()
    for fragment in (
        "bootstrap_target", "bootstrap_policy", "bootstrap_authority",
        "ck_mh_supervisor_cleanup_retention_bootstrap_duration",
    ):
        assert fragment in text


def test_recovery_binds_historical_target_and_both_revisions() -> None:
    text = _text()
    for fragment in (
        "authority_recovery_target", "authority_recovery_expected",
        "authority_recovery_result",
    ):
        assert fragment in text


def test_downgrade_is_exact_reverse_dependency_order() -> None:
    section = _text().split("def downgrade() -> None:", 1)[1]
    expected = (
        "_RECOVERIES", "_BOOTSTRAPS", "_AUTHORITY_CHANGES", "_CHANGES",
        "_CURRENT", "_ACTIVE", "_MEMBERS", "_SETS", "_POLICIES",
    )
    positions = [section.index(f"op.drop_table({name})") for name in expected]
    assert positions == sorted(positions)


def test_current_inventory_and_roadmap_are_synchronized() -> None:
    gate = (ROOT / "tests/test_persistence_migration_gate.py").read_text(encoding="utf-8")
    bundle = (ROOT / "tools/operational_release_bundle.py").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    migrations = list((ROOT / "src/liquent_platform/persistence/alembic/versions").glob("*.py"))
    assert len(migrations) == 42
    assert 'expected_head() == "20260826_0042"' in gate
    assert "EXPECTED_MIGRATION_COUNT = 42" in bundle
    assert "**42 lineare Migrationen**, Head\n  `20260826_0042`" in roadmap
    assert "- LQ-532 persistent supervisor cleanup retention policy and authority foundation:" in roadmap
    assert "nächster Slice LQ-533" in roadmap
