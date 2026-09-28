import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
DOMAIN = ROOT / "src/liquent_platform/identity/manifest_handoff_supervisor_control_directory_cleanup_execution.py"
PORTS = ROOT / "src/liquent_platform/identity/ports.py"


def _domain() -> str:
    return DOMAIN.read_text(encoding="utf-8")


def test_two_internal_ids_are_repr_free_and_strict() -> None:
    text = _domain()
    for name in (
        "ManifestHandoffSupervisorControlDirectoryCleanupPreflightId",
        "ManifestHandoffSupervisorControlDirectoryCleanupWriteClaimId",
    ):
        assert f"class {name}:" in text
    assert text.count("value: str = field(repr=False)") == 2
    assert "type(value) is not str or not value or value.strip() != value" in text


def test_preflight_request_contains_only_attempt_and_directory() -> None:
    text = _domain()
    section = text[text.index("class PreflightManifestHandoffSupervisorControlDirectoryCleanup"):
                   text.index("class PreparedManifestHandoffSupervisorControlDirectoryCleanup")]
    assert "attempt_id: ManifestHandoffSupervisorControlDirectoryCleanupAttemptId" in section
    assert "directory_id: ManifestHandoffSupervisorControlDirectoryId" in section
    for forbidden in ("actor", "allow", "path", "root", "leaf", "clearance_id"):
        assert forbidden not in section.lower()


def test_prepared_and_absent_bind_current_clearance_without_physical_details() -> None:
    text = _domain()
    for name in (
        "PreparedManifestHandoffSupervisorControlDirectoryCleanup",
        "AbsentManifestHandoffSupervisorControlDirectoryCleanupPreflight",
    ):
        section = text[text.index(f"class {name}"):]
        assert "attempt_id: ManifestHandoffSupervisorControlDirectoryCleanupAttemptId" in section
        assert "directory_id: ManifestHandoffSupervisorControlDirectoryId" in section
        assert "clearance_id: ManifestHandoffSupervisorControlDirectoryCleanupClearanceId" in section
    assert "prepared_at: datetime" in text
    assert "observed_at: datetime" in text


def test_claim_wraps_prepared_and_projects_target_with_monotone_time() -> None:
    text = _domain()
    assert "class ClaimPreparedManifestHandoffSupervisorControlDirectoryCleanup:" in text
    assert "prepared: PreparedManifestHandoffSupervisorControlDirectoryCleanup" in text
    claimed = text[text.index("class ClaimedManifestHandoffSupervisorControlDirectoryCleanup"):
                   text.index("class RemovedManifestHandoffSupervisorControlDirectory")]
    assert "claim_id: ManifestHandoffSupervisorControlDirectoryCleanupWriteClaimId" in claimed
    assert "if self.claimed_at < self.prepared.prepared_at" in claimed
    assert "return self.prepared.attempt_id" in claimed
    assert "return self.prepared.directory_id" in claimed


def test_removed_and_unknown_bind_claim_attempt_and_directory() -> None:
    text = _domain()
    for name in (
        "RemovedManifestHandoffSupervisorControlDirectory",
        "UnknownManifestHandoffSupervisorControlDirectoryCleanupEffect",
    ):
        section = text[text.index(f"class {name}"):]
        assert "claim_id: ManifestHandoffSupervisorControlDirectoryCleanupWriteClaimId" in section
        assert "attempt_id: ManifestHandoffSupervisorControlDirectoryCleanupAttemptId" in section
        assert "directory_id: ManifestHandoffSupervisorControlDirectoryId" in section
    assert "removed_at: datetime" in text


def test_reconciliation_inspection_is_closed_read_only_observation() -> None:
    text = _domain()
    section = text[text.index("class InspectedManifestHandoffSupervisorControlDirectoryCleanupReconciliation"):]
    assert "request: ReconcileManifestHandoffSupervisorControlDirectoryCleanup" in section
    assert "outcome: ManifestHandoffSupervisorControlDirectoryCleanupReconciliationOutcome" in section
    assert "inspected_at: datetime" in section


def test_four_minimal_ports_have_exact_methods() -> None:
    text = PORTS.read_text(encoding="utf-8")
    for cls, method in (
        ("ManifestHandoffSupervisorControlDirectoryCleanupPreflight", "prepare_control_directory_cleanup"),
        ("ManifestHandoffSupervisorControlDirectoryCleanupWriteClaim", "claim_control_directory_cleanup_write"),
        ("ManifestHandoffSupervisorControlDirectoryPhysicalCleanup", "remove_control_directory"),
        ("ManifestHandoffSupervisorControlDirectoryPhysicalCleanupReconciliation", "inspect_control_directory_cleanup"),
    ):
        assert f"class {cls}(Protocol):" in text
        section = text[text.index(f"class {cls}(Protocol):"):]
        assert f"def {method}(" in section


def test_physical_port_cannot_return_neutral_none_after_claim() -> None:
    text = PORTS.read_text(encoding="utf-8")
    section = text[text.index("class ManifestHandoffSupervisorControlDirectoryPhysicalCleanup(Protocol):"):
                   text.index("class ManifestHandoffSupervisorControlDirectoryCleanupPhysicalOutcomeStore(Protocol):")]
    assert "UnknownManifestHandoffSupervisorControlDirectoryCleanupEffect" in section
    assert "| None" not in section


def test_domain_has_no_path_io_schema_authority_or_wiring_surface() -> None:
    text = _domain()
    ast.parse(text)
    for forbidden in (
        "from pathlib", "import os", "sqlalchemy", "open(", "unlink", "rmdir",
        "SessionPrincipal", "UserId", "WorkspaceId", "Permission", "allowed",
        "CREATE TABLE", "create_app",
    ):
        assert forbidden not in text


def test_roadmap_records_lq510_and_lq511() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-510 closed physical cleanup execution values and ports:" in roadmap
    assert "lq-510-closed-physical-cleanup-execution-values-and-ports.md" in roadmap
    assert "nächster Slice LQ-511" in roadmap
