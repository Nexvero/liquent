import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
DOMAIN = ROOT / "src/liquent_platform/identity/manifest_handoff_supervisor_control_directory_cleanup_clearance.py"
PORTS = ROOT / "src/liquent_platform/identity/ports.py"


def _domain() -> str:
    return DOMAIN.read_text(encoding="utf-8")


def test_five_clearance_ids_are_repr_free() -> None:
    text = _domain()
    for suffix in (
        "CleanupClearanceId", "CleanupManagementRevisionId", "CleanupHoldRevisionId",
        "CleanupRecoveryRevisionId", "CleanupReferenceRevisionId",
    ):
        assert f"class ManifestHandoffSupervisorControlDirectory{suffix}:" in text
    assert text.count("value: str = field(repr=False)") == 5


def test_management_and_clearance_dispositions_are_closed() -> None:
    text = _domain()
    assert 'ACTIVE = "active"' in text and 'INACTIVE = "inactive"' in text
    assert 'CLEAR = "clear"' in text and 'BLOCKED = "blocked"' in text
    assert "class ManifestHandoffSupervisorControlDirectoryCleanupManagementAuthority" in text


def test_hold_recovery_and_reference_decisions_bind_full_retired() -> None:
    text = _domain()
    for name, revision in (
        ("HoldDecision", "HoldRevisionId"),
        ("RecoveryDecision", "RecoveryRevisionId"),
        ("ReferenceDecision", "ReferenceRevisionId"),
    ):
        section = text[text.index(f"class ManifestHandoffSupervisorControlDirectoryCleanup{name}"):]
        assert f"revision_id: ManifestHandoffSupervisorControlDirectoryCleanup{revision}" in section
        assert "retired: RetiredManifestHandoffSupervisorControlDirectory" in section
    assert "value.decided_at < value.retired.retired_at" in text


def test_aggregate_carries_request_retired_scope_full_journal_and_all_evidence() -> None:
    text = _domain()
    section = text[text.index("class ClearedManifestHandoffSupervisorControlDirectoryCleanup"):]
    for field in (
        "request: CleanupManifestHandoffSupervisorControlDirectory",
        "retired: RetiredManifestHandoffSupervisorControlDirectory",
        "scope_id: ManifestHandoffRegistryScopeId",
        "journal: ManifestHandoffWriterJournalView | ManifestHandoffRecoveryJournalView",
        "decision: ManifestHandoffSupervisorControlDirectoryCleanupDecision",
        "management:", "hold:", "recovery:", "references:",
    ):
        assert field in section


def test_aggregate_validates_terminal_handle_scope_actor_and_directory_bindings() -> None:
    text = _domain()
    for evidence in (
        "ManifestHandoffSupervisorJournalState.TERMINAL_OBSERVED",
        "self.journal.registration.handle_id == self.retired.handle_id",
        "self.journal.result.handle_id == self.retired.handle_id",
        "self.journal.registration.process_request.binding.scope_id == self.scope_id",
        "self.management.actor_user_id == self.request.actor_user_id",
        "self.management.scope_id == self.scope_id",
        "self.request.directory_id == self.retired.directory_id",
    ):
        assert evidence in text


def test_aggregate_requires_only_positive_current_dispositions() -> None:
    text = _domain()
    for evidence in (
        "CleanupManagementStatus.ACTIVE",
        "CleanupDisposition.ELIGIBLE",
        "self.hold.disposition is ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition.CLEAR",
        "self.recovery.disposition is ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition.CLEAR",
        "self.references.disposition is ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition.CLEAR",
    ):
        assert evidence in text
    assert "self.cleared_at < latest_fact" in text


def test_five_minimal_read_only_resolver_ports_are_added() -> None:
    text = PORTS.read_text(encoding="utf-8")
    for cls, method in (
        ("CleanupManagementLookup", "resolve_control_directory_cleanup_management"),
        ("CleanupHoldLookup", "resolve_control_directory_cleanup_hold"),
        ("CleanupRecoveryLookup", "resolve_control_directory_cleanup_recovery"),
        ("CleanupReferenceLookup", "resolve_control_directory_cleanup_references"),
        ("CleanupClearanceResolution", "resolve_control_directory_cleanup_clearance"),
    ):
        assert f"class ManifestHandoffSupervisorControlDirectory{cls}(Protocol):" in text
        assert f"def {method}(" in text


def test_no_path_file_schema_mutation_or_session_authority() -> None:
    text = _domain()
    for forbidden in (
        "from pathlib", "import os", "sqlalchemy", "open(", "unlink", "rmdir",
        "SessionPrincipal", "WorkspaceId", "Permission", "allowed",
    ):
        assert forbidden not in text


def test_roadmap_records_lq496_and_lq497() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-496 closed supervisor control-directory cleanup clearance values and ports:" in roadmap
    assert "lq-496-closed-supervisor-control-directory-cleanup-clearance-values-and-ports.md" in roadmap
    assert "nächster Slice LQ-497" in roadmap
