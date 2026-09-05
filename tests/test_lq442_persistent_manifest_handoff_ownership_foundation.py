import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
MIGRATION = ROOT / "src/liquent_platform/persistence/alembic/versions/20260824_0029_manifest_handoff_execution_ownership.py"


def test_revision_is_linear_additive_and_empty() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert 'revision: str = "20260824_0029"' in text
    assert 'down_revision: str | Sequence[str] | None = "20260819_0028"' in text
    assert "op.bulk_insert" not in text
    assert "INSERT" not in text
    assert "UPDATE" not in text
    assert "op.drop_table" in text


def test_foundation_has_all_ownership_and_recovery_tables() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    for table in (
        "manifest_handoff_recovery_authorities",
        "manifest_handoff_execution_claims",
        "manifest_handoff_execution_lease_renewals",
        "manifest_handoff_execution_starts",
        "manifest_handoff_execution_ends",
        "manifest_handoff_recovery_claims",
        "manifest_handoff_recovery_ends",
        "manifest_handoff_recovery_observations",
    ):
        assert f'"{table}"' in text


def test_execution_claim_is_permanent_and_start_is_claim_bound() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert '"attempt_id", name="uq_manifest_handoff_execution_attempt"' in text
    assert "lease_expires_at>claimed_at" in text
    assert '"observation_id", name="uq_manifest_handoff_execution_start_observation"' in text
    assert '"manifest_handoff_execution_claims.claim_id"' in text
    assert '"manifest_handoff_attempt_observations.observation_id"' in text


def test_lease_and_terminal_evidence_are_append_only_by_identity() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert '"renewal_id", name="pk_manifest_handoff_execution_lease_renewals"' in text
    assert "lease_expires_at>renewed_at" in text
    assert '"end_id", name="pk_manifest_handoff_execution_ends"' in text
    assert '"claim_id", name="uq_manifest_handoff_execution_end_claim"' in text
    assert "'outcome_secured','outcome_unknown','start_not_confirmed'" in text
    assert "ondelete=" not in text


def test_recovery_authority_and_single_active_claim_fail_closed() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert "status IN ('active','inactive')" in text
    assert "uq_manifest_handoff_active_recovery_attempt" in text
    assert text.count('sa.text("ended_at IS NULL")') == 2
    assert '"execution_end_id"' in text
    assert '"manifest_handoff_execution_ends.end_id"' in text
    assert '"claim_id", name="uq_manifest_handoff_recovery_end_claim"' in text


def test_recovery_observation_is_one_to_one_and_no_writer_kind_is_added() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert '"claim_id", name="pk_manifest_handoff_recovery_observations"' in text
    assert '"observation_id", name="uq_manifest_handoff_recovery_observation"' in text
    assert "writer_started" not in text
    assert "cleanup_completed" not in text


def test_domain_and_ports_add_stable_renewal_and_recovery_end_sources() -> None:
    domain = ast.parse(
        (ROOT / "src/liquent_platform/identity/manifest_handoff.py").read_text()
    )
    ports = ast.parse((ROOT / "src/liquent_platform/identity/ports.py").read_text())
    domain_names = {node.name for node in domain.body if isinstance(node, ast.ClassDef)}
    assert {
        "ManifestHandoffLeaseRenewalId",
        "ManifestHandoffRecoveryEndId",
        "ManifestHandoffRecoveryEndKind",
        "RecordedManifestHandoffRecoveryEnd",
    } <= domain_names
    recovery_end = next(
        node for node in ports.body
        if isinstance(node, ast.ClassDef)
        and node.name == "ControlledManifestHandoffRecoveryEnd"
    )
    assert [
        node.name for node in recovery_end.body if isinstance(node, ast.FunctionDef)
    ] == ["record_outcome_secured", "record_outcome_unknown", "record_start_not_confirmed"]


def test_current_migration_gates_are_synchronized() -> None:
    gate = (ROOT / "tests/test_persistence_migration_gate.py").read_text()
    bundle = (ROOT / "tools/operational_release_bundle.py").read_text()
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    assert 'expected_head() == "20260826_0042"' in gate
    assert "EXPECTED_MIGRATION_COUNT = 42" in bundle
    assert "**42 lineare Migrationen**, Head\n  `20260826_0042`" in roadmap


def test_roadmap_records_foundation_and_next_slice() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    assert "- LQ-442 persistent manifest handoff ownership and recovery foundation:" in roadmap
    assert "`docs/lq-442-persistent-manifest-handoff-ownership-and-recovery-foundation.md`" in roadmap
    assert "nächster Slice LQ-443" in roadmap
