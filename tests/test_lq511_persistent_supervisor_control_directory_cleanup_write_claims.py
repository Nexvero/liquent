from pathlib import Path


ROOT = Path(__file__).parents[1]
MIGRATION = ROOT / "src/liquent_platform/persistence/alembic/versions/20260826_0040_supervisor_control_directory_cleanup_write_claims.py"
ADAPTER = ROOT / "src/liquent_platform/persistence/manifest_handoff_supervisor_control_directory_cleanup_write_claim.py"
CLEANUP = ROOT / "src/liquent_platform/persistence/manifest_handoff_supervisor_control_directory_cleanup.py"


def test_revision_is_linear_after_0039_and_empty() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert 'revision: str = "20260826_0040"' in text
    assert 'down_revision: str | Sequence[str] | None = "20260826_0039"' in text
    for forbidden in ("INSERT ", "UPDATE ", "DELETE ", "op.bulk_insert"):
        assert forbidden not in text


def test_claim_table_binds_non_reusable_claim_attempt_and_preflight() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert '"manifest_handoff_supervisor_control_cleanup_write_claims"' in text
    assert 'sa.PrimaryKeyConstraint("claim_id"' in text
    assert 'sa.UniqueConstraint("attempt_id"' in text
    assert 'sa.UniqueConstraint("preflight_id"' in text
    assert '"length(claim_id)>0"' in text
    assert '"length(preflight_id)>0"' in text


def test_composite_foreign_keys_bind_attempt_directory_and_clearance() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert '["attempt_id", "directory_id"]' in text
    assert '["clearance_id", "attempt_id", "directory_id"]' in text
    assert "uq_mh_supervisor_control_cleanup_attempt_binding" in text
    assert "uq_mh_supervisor_cleanup_clearance_attempt_binding" in text


def test_attempt_state_machine_has_distinct_claim_and_ordering() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert "'started','write_claimed','outcome_unknown','completed','reconciled'" in text
    assert "state='write_claimed' AND write_claimed_at IS NOT NULL" in text
    assert "outcome='removed' AND write_claimed_at IS NOT NULL" in text
    assert "outcome='already_absent' AND write_claimed_at IS NULL" in text
    assert "unknown_at>=write_claimed_at" in text
    assert "claimed_at>=prepared_at" in text


def test_unresolved_index_includes_claimed_state() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    predicate = "state IN ('started','write_claimed','outcome_unknown')"
    assert text.count(predicate) == 2


def test_adapter_is_retry_first_and_rejects_partial_foundation() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    section = text[text.index("def claim_control_directory_cleanup_write"):text.index("def _base_binding")]
    assert section.index("attempt = self._one") < section.index("self._clearances._facts")
    assert section.index("claim = self._one") < section.index("self._clearances._facts")
    assert "if attempt is None" in section
    assert "if clearance is None" in section
    assert "return self._retry(attempt, claim, prepared)" in section


def test_new_claim_revalidates_all_current_clearance_sources() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    assert "self._clearances._facts" in text
    for field in (
        "terminal_observation_id", "decision_id", "management_revision_id",
        "hold_revision_id", "recovery_revision_id", "reference_revision_id",
    ):
        assert f"clearance.{field}" in text


def test_claim_insert_and_conditional_transition_share_transaction() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    section = text[text.index("INSERT INTO manifest_handoff_supervisor_control_cleanup_write_claims"):
                   text.index("return ClaimedManifestHandoffSupervisorControlDirectoryCleanup")]
    assert "SET state='write_claimed',write_claimed_at=:claimed" in section
    assert "state='started'" in section
    assert "changed.rowcount != 1" in section
    assert "with self._engine.begin()" in text


def test_existing_cleanup_transitions_require_claim_for_effects() -> None:
    text = CLEANUP.read_text(encoding="utf-8")
    assert 'expected="write_claimed", target="outcome_unknown"' in text
    assert 'outcome is ManifestHandoffSupervisorControlDirectoryCleanupOutcome.REMOVED' in text
    assert "return ClaimedManifestHandoffSupervisorControlDirectoryCleanup(" in text


def test_no_path_file_wiring_or_new_exception_surface() -> None:
    text = ADAPTER.read_text(encoding="utf-8") + MIGRATION.read_text(encoding="utf-8")
    for forbidden in ("from pathlib", "import os", "open(", "unlink", "rmdir", "create_app", "SessionPrincipal"):
        assert forbidden not in text


def test_current_head_bundle_and_roadmap_are_synchronized() -> None:
    gate = (ROOT / "tests/test_persistence_migration_gate.py").read_text(encoding="utf-8")
    bundle = (ROOT / "tools/operational_release_bundle.py").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert 'expected_head() == "20260826_0042"' in gate
    assert "EXPECTED_MIGRATION_COUNT = 42" in bundle
    assert "**42 lineare Migrationen**, Head\n  `20260826_0042`" in roadmap


def test_roadmap_records_lq511_and_lq512() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-511 persistent supervisor control-directory cleanup write claims:" in roadmap
    assert "lq-511-persistent-supervisor-control-directory-cleanup-write-claims.md" in roadmap
    assert "nächster Slice LQ-512" in roadmap
