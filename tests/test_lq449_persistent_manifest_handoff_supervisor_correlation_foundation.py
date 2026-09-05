from pathlib import Path


ROOT = Path(__file__).parents[1]
MIGRATION = ROOT / "src/liquent_platform/persistence/alembic/versions/20260824_0030_manifest_handoff_supervisor_correlations.py"


def test_revision_is_linear_additive_and_empty() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert 'revision: str = "20260824_0030"' in text
    assert 'down_revision: str | Sequence[str] | None = "20260824_0029"' in text
    assert "op.bulk_insert" not in text
    assert "INSERT" not in text
    assert "UPDATE" not in text


def test_exactly_six_correlation_tables_are_added() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    tables = (
        "manifest_handoff_supervisor_backends",
        "manifest_handoff_supervisor_preparations",
        "manifest_handoff_supervisor_handle_bindings",
        "manifest_handoff_supervisor_releases",
        "manifest_handoff_supervisor_terminations",
        "manifest_handoff_supervisor_terminal_observations",
    )
    assert text.count("op.create_table(") == len(tables)
    for table in tables:
        assert f'"{table}"' in text


def test_backend_and_prepare_claim_shape_fail_closed() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert "status IN ('active','inactive')" in text
    assert "capability='writer' AND execution_claim_id IS NOT NULL" in text
    assert "capability='recovery' AND execution_claim_id IS NULL" in text
    assert '"execution_claim_id", name="uq_manifest_handoff_supervisor_execution_claim"' in text
    assert '"recovery_claim_id", name="uq_manifest_handoff_supervisor_recovery_claim"' in text


def test_handle_and_operations_are_one_to_one_append_facts() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert '"prepare_id", name="uq_manifest_handoff_supervisor_handle_prepare"' in text
    assert '"handle_id", name="uq_manifest_handoff_supervisor_release_handle"' in text
    assert '"handle_id", name="uq_manifest_handoff_supervisor_terminate_handle"' in text
    assert '"handle_id", name="uq_manifest_handoff_supervisor_terminal_handle"' in text
    assert "current_state" not in text
    assert "gate_released" not in text


def test_foreign_keys_are_closed_and_downgrade_is_reverse_order() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    for target in (
        "manifest_handoff_execution_claims.claim_id",
        "manifest_handoff_recovery_claims.claim_id",
        "manifest_handoff_supervisor_preparations.prepare_id",
        "manifest_handoff_supervisor_handle_bindings.handle_id",
    ):
        assert target in text
    assert '["prepare_id", "backend_instance_id"]' in text
    assert "fk_manifest_handoff_supervisor_handle_prepare_backend" in text
    assert "ondelete=" not in text
    drops = [line.strip() for line in text.splitlines() if "op.drop_table" in line]
    assert drops[0].endswith('("manifest_handoff_supervisor_terminal_observations")')
    assert drops[-1].endswith('("manifest_handoff_supervisor_backends")')


def test_current_migration_gates_are_synchronized() -> None:
    gate = (ROOT / "tests/test_persistence_migration_gate.py").read_text()
    bundle = (ROOT / "tools/operational_release_bundle.py").read_text()
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    assert 'expected_head() == "20260826_0042"' in gate
    assert "EXPECTED_MIGRATION_COUNT = 42" in bundle
    assert "**42 lineare Migrationen**, Head\n  `20260826_0042`" in roadmap


def test_roadmap_records_foundation_and_next_slice() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    assert "- LQ-449 persistent manifest handoff supervisor correlation foundation:" in roadmap
    assert "lq-449-persistent-manifest-handoff-supervisor-correlation-foundation.md" in roadmap
    assert "nächster Slice LQ-450" in roadmap
