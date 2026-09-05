from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTS = ROOT / "src/liquent_platform/identity/ports.py"
ADAPTER = ROOT / "src/liquent_platform/persistence/manifest_handoff_supervisor_control_directory_cleanup.py"


def _text() -> str:
    return ADAPTER.read_text(encoding="utf-8")


def test_one_minimal_physical_outcome_store_port_is_added() -> None:
    text = PORTS.read_text(encoding="utf-8")
    section = text[text.index("class ManifestHandoffSupervisorControlDirectoryCleanupPhysicalOutcomeStore"):
                   text.index("class ManifestHandoffSupervisorControlDirectoryPhysicalCleanupReconciliation")]
    assert "def persist_control_directory_cleanup_physical_outcome(" in section
    assert "RemovedManifestHandoffSupervisorControlDirectory" in section
    assert "UnknownManifestHandoffSupervisorControlDirectoryCleanupEffect" in section
    assert "CompletedManifestHandoffSupervisorControlDirectoryCleanup" in section
    assert "ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired" in section


def test_adapter_accepts_only_two_closed_physical_outcomes() -> None:
    text = _text()
    section = text[text.index("def persist_control_directory_cleanup_physical_outcome"):
                   text.index("def record_cleanup_reconciliation")]
    assert "type(outcome) not in (" in section
    assert "RemovedManifestHandoffSupervisorControlDirectory" in section
    assert "UnknownManifestHandoffSupervisorControlDirectoryCleanupEffect" in section
    assert "raise ManifestHandoffRegistryUnavailable" in section


def test_unknown_attempt_is_neutral_and_every_known_target_is_bound() -> None:
    text = _text()
    section = text[text.index("def persist_control_directory_cleanup_physical_outcome"):
                   text.index("def record_cleanup_reconciliation")]
    assert "if row is None:\n                return None" in section
    assert "_decode(row.directory_id) != outcome.directory_id.value" in section
    assert "row.state != \"write_claimed\"" in section
    assert "claimed.claim_id != outcome.claim_id" in section


def test_removed_uses_physical_time_and_unknown_uses_internal_clock() -> None:
    text = _text()
    assert "if outcome.removed_at < claimed.claimed_at" in text
    assert "completed_at=:at" in text
    assert "at = outcome.removed_at" in text
    assert "at = _utc(self._clock())" in text
    assert "if at < claimed.claimed_at" in text
    assert "state='outcome_unknown',unknown_at=:at" in text


def test_conditional_update_is_claim_bound_and_exactly_once() -> None:
    text = _text()
    section = text[text.index("UPDATE manifest_handoff_supervisor_control_cleanup_attempts"):
                   text.index("return result", text.index("UPDATE manifest_handoff_supervisor_control_cleanup_attempts"))]
    assert "state='write_claimed'" in section
    assert "manifest_handoff_supervisor_control_cleanup_write_claims claim" in section
    assert "claim.claim_id=:claim" in section
    assert "changed.rowcount != 1" in section


def test_direct_generic_completion_is_already_absent_only() -> None:
    text = _text()
    section = text[text.index("def complete_cleanup_attempt"):
                   text.index("def persist_control_directory_cleanup_physical_outcome")]
    assert "outcome is not ManifestHandoffSupervisorControlDirectoryCleanupOutcome.ALREADY_ABSENT" in section
    assert 'expected="started", target="completed"' in section
    assert "ManifestHandoffSupervisorControlDirectoryCleanupOutcome.REMOVED" not in section


def test_exact_retry_reconstructs_only_matching_terminal_outcome() -> None:
    text = _text()
    assert 'if row.state in ("completed", "outcome_unknown")' in text
    assert "return self._physical_outcome_retry(row, outcome)" in text
    retry = text[text.index("def _physical_outcome_retry"):text.index("def _retry_request")]
    assert "claimed.claim_id != outcome.claim_id" in retry
    assert "current.completed_at == outcome.removed_at" in retry
    assert "type(current) is ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired" in retry
    assert "return ManifestHandoffSupervisorControlDirectoryCleanupConflict()" in retry


def test_adapter_adds_no_file_schema_authority_or_wiring_effect() -> None:
    text = _text()
    for forbidden in (
        "from pathlib", "import os", "unlink", "rmdir", "mkdir", "create_app",
        "SessionPrincipal", "WorkspaceId", "Permission", "ALTER TABLE",
        "CREATE TABLE",
    ):
        assert forbidden not in text


def test_roadmap_records_lq514_and_lq515() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-514 claim-bound persistent physical cleanup outcomes:" in roadmap
    assert "lq-514-claim-bound-persistent-physical-cleanup-outcomes.md" in roadmap
    assert "nächster Slice LQ-515" in roadmap
