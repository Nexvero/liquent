from pathlib import Path


ROOT = Path(__file__).parents[1]
MIGRATION = ROOT / "src/liquent_platform/persistence/alembic/versions/20260824_0031_manifest_handoff_supervisor_journal.py"


def test_revision_is_linear_empty_and_additive() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert 'revision: str = "20260824_0031"' in text
    assert 'down_revision: str | Sequence[str] | None = "20260824_0030"' in text
    assert "INSERT" not in text and "UPDATE" not in text and "op.bulk_insert" not in text


def test_exactly_job_and_append_transition_tables_are_added() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert text.count("op.create_table(") == 2
    assert '"manifest_handoff_supervisor_journal_jobs"' in text
    assert '"manifest_handoff_supervisor_journal_transitions"' in text
    assert "op.drop_table(\"manifest_handoff_supervisor_journal_transitions\")" in text


def test_job_binding_is_unique_and_capability_claim_is_closed() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert "uq_manifest_handoff_supervisor_journal_prepare" in text
    assert "uq_manifest_handoff_supervisor_journal_launch" in text
    assert "capability='writer' AND execution_claim_id IS NOT NULL" in text
    assert "capability='recovery' AND execution_claim_id IS NULL" in text
    assert "length(source_root)>0 AND length(target_root)>0" in text


def test_transitions_are_append_only_unique_and_job_bound() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert "uq_manifest_handoff_supervisor_journal_sequence" in text
    assert "uq_manifest_handoff_supervisor_journal_kind" in text
    assert "sequence_number>0" in text
    assert "fk_manifest_handoff_supervisor_journal_transition_job" in text
    assert "current_state" not in text and "gate_released" not in text


def test_terminal_payload_and_capability_outcomes_are_closed() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert "kind<>'terminal_observed' AND outcome_kind IS NULL" in text
    assert "ck_manifest_handoff_supervisor_journal_outcome_capability" in text
    assert "ck_manifest_handoff_supervisor_journal_outcome_facts" in text
    assert "length(manifest_sha256)=64 AND file_count>0" in text


def test_migration_gates_are_synchronized_to_31() -> None:
    gate = (ROOT / "tests/test_persistence_migration_gate.py").read_text()
    bundle = (ROOT / "tools/operational_release_bundle.py").read_text()
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    assert 'expected_head() == "20260826_0042"' in gate
    assert "EXPECTED_MIGRATION_COUNT = 42" in bundle
    assert "**42 lineare Migrationen**, Head\n  `20260826_0042`" in roadmap


def test_roadmap_records_lq454_and_next_adapter() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    assert "- LQ-454 persistent manifest handoff supervisor journal foundation:" in roadmap
    assert "lq-454-persistent-manifest-handoff-supervisor-journal-foundation.md" in roadmap
    assert "nächster Slice LQ-455" in roadmap
