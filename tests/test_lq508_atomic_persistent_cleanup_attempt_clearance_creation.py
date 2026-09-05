import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "src/liquent_platform/persistence/manifest_handoff_supervisor_cleanup_clearance_creation.py"
JOURNAL = ROOT / "src/liquent_platform/persistence/manifest_handoff_supervisor_journal.py"


def _text() -> str:
    return ADAPTER.read_text(encoding="utf-8")


def test_creation_port_method_and_principal_request_binding_exist() -> None:
    text = _text()
    assert "def create_control_directory_cleanup_clearance(self, principal, request):" in text
    assert "type(principal) is not SessionPrincipal" in text
    assert "type(request) is not CleanupManifestHandoffSupervisorControlDirectory" in text
    assert "principal.user_id != request.actor_user_id" in text


def test_retry_and_non_adoption_check_precede_new_fact_resolution() -> None:
    text = _text()
    section = text[text.index("def create_control_directory_cleanup_clearance"):text.index("def _retry")]
    assert section.index("attempt = self._one") < section.index("facts = self._facts")
    assert section.index("clearance = self._one") < section.index("facts = self._facts")
    assert "if attempt is None or clearance is None" in section
    assert "CleanupConflict()" in section


def test_retry_revalidates_all_current_bound_revisions() -> None:
    text = _text()
    section = text[text.index("def _retry"):text.index("def _facts")]
    assert "facts = self._facts" in section
    for field in ("decision_id", "management_revision_id", "hold_revision_id",
                  "recovery_revision_id", "reference_revision_id", "terminal_observation_id"):
        assert f"clearance.{field}" in section


def test_journal_reconstruction_reuses_existing_validation_inside_transaction() -> None:
    text = _text()
    journal = JOURNAL.read_text(encoding="utf-8")
    assert "DatabaseManifestHandoffSupervisorJournal.reconstruct_view(job, history)" in text
    assert "def reconstruct_view(cls, job, history):" in journal
    assert "return cls._view(job, history)" in journal
    assert "state = cls._validate_history(job, history)" in journal


def test_facts_require_retired_full_terminal_and_active_actor_scope() -> None:
    text = _text()
    section = text[text.index("def _facts"):text.index("def _active_foundations")]
    assert "DatabaseManifestHandoffSupervisorControlDirectories._lifecycle" in section
    assert "RetiredManifestHandoffSupervisorControlDirectory" in section
    assert "ManifestHandoffSupervisorJournalState.TERMINAL_OBSERVED" in section
    assert "journal.terminal_observation_id is None or journal.result is None" in section
    assert "journal.registration.process_request.binding.scope_id" in section
    assert "_active_foundations" in section


def test_all_five_current_sources_must_be_positive() -> None:
    text = _text()
    section = text[text.index("def _facts"):text.index("def _active_foundations")]
    assert "CleanupDisposition.ELIGIBLE" in section
    assert "CleanupManagementStatus.ACTIVE" in section
    assert section.count("CleanupClearanceDisposition.CLEAR") == 1
    assert 'for kind in ("hold", "recovery", "reference")' in section


def test_clearance_id_and_time_are_internal_and_monotone() -> None:
    text = _text()
    assert "clearance_id = self._new_clearance_id()" in text
    assert "self._clearance()" in text
    assert "lower = max(retired.retired_at" in text
    assert "if now < lower" in text
    assert '"now": now' in text


def test_attempt_and_clearance_are_inserted_in_one_transaction_in_order() -> None:
    text = _text()
    section = text[text.index("def create_control_directory_cleanup_clearance"):text.index("def _retry")]
    attempt = section.index("INSERT INTO manifest_handoff_supervisor_control_cleanup_attempts")
    clearance = section.index("INSERT INTO manifest_handoff_supervisor_cleanup_clearances")
    assert attempt < clearance
    assert "self._engine.begin()" in text
    assert "'started'" in section
    assert "NULL,NULL,NULL,NULL,NULL" in section


def test_postgres_lock_sqlite_and_detail_free_boundary_exist() -> None:
    text = _text()
    assert "LOCK TABLE identity_users,manifest_handoff_registry_scopes" in text
    for table in ("control_directories", "journal_jobs", "journal_transitions",
                  "cleanup_decisions", "management_revisions", "hold_revisions",
                  "recovery_revisions", "reference_revisions", "cleanup_attempts",
                  "cleanup_clearances"):
        assert table in text[text.index("LOCK TABLE"):]
    assert 'connection.dialect.name != "sqlite"' in text
    assert "ManifestHandoffRegistryUnavailable" in text


def test_no_source_mutation_file_execution_or_wiring_effect() -> None:
    text = _text()
    for forbidden in (
        "INSERT INTO manifest_handoff_supervisor_cleanup_management_revisions",
        "INSERT INTO manifest_handoff_supervisor_cleanup_hold_revisions",
        "INSERT INTO manifest_handoff_supervisor_cleanup_recovery_revisions",
        "INSERT INTO manifest_handoff_supervisor_cleanup_reference_revisions",
        "from pathlib", "open(", "unlink", "rmdir", "create_app",
        "cleanup_control_directory(", "WorkspaceId", "Permission",
    ):
        assert forbidden not in text


def test_roadmap_records_lq508_and_lq509() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-508 atomic persistent cleanup attempt clearance creation:" in roadmap
    assert "lq-508-atomic-persistent-cleanup-attempt-clearance-creation.md" in roadmap
    assert "nächster Slice LQ-509" in roadmap
