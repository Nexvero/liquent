import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTS = ROOT / "src/liquent_platform/identity/ports.py"
CLAIMS = ROOT / "src/liquent_platform/persistence/manifest_handoff_supervisor_control_directory_cleanup_write_claim.py"
LOCAL = ROOT / "src/liquent_platform/transport/manifest_handoff_supervisor_control_directory_cleanup_reconciliation.py"
APPLICATION = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_control_directory_cleanup_reconciliation.py"


def test_minimal_historical_claim_lookup_port_and_adapter_exist() -> None:
    ports = PORTS.read_text(encoding="utf-8")
    claims = CLAIMS.read_text(encoding="utf-8")
    assert "class ManifestHandoffSupervisorControlDirectoryCleanupWriteClaimLookup(Protocol):" in ports
    assert "def resolve_control_directory_cleanup_write_claim(" in ports
    assert "def resolve_control_directory_cleanup_write_claim(self, attempt_id):" in claims
    assert "_CLAIM_VIEW" in claims


def test_claim_lookup_reconstructs_only_claim_derived_states_and_times() -> None:
    text = CLAIMS.read_text(encoding="utf-8")
    section = text[text.index("def resolve_control_directory_cleanup_write_claim"):text.index("def _base_binding")]
    assert 'row.state not in ("write_claimed", "outcome_unknown", "completed", "reconciled")' in section
    assert 'row.state == "completed" and row.outcome != "removed"' in section
    assert "_utc(row.write_claimed_at) != claimed_at" in section
    assert "prepared_at < _utc(row.started_at)" in section
    assert "claimed_at < prepared_at" in section
    assert "PreparedManifestHandoffSupervisorControlDirectoryCleanup(" in section
    assert "ClaimedManifestHandoffSupervisorControlDirectoryCleanup(" in section


def test_local_inspector_accepts_only_claimed_or_unknown_attempts() -> None:
    text = LOCAL.read_text(encoding="utf-8")
    assert "type(attempt) not in (" in text
    assert "ClaimedManifestHandoffSupervisorControlDirectoryCleanup" in text
    assert "ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired" in text
    assert "claimed = self._claims(request.attempt_id)" in text
    assert "claimed.directory_id != request.directory_id" in text


def test_local_inspection_classifies_absent_present_and_conflict() -> None:
    text = LOCAL.read_text(encoding="utf-8")
    assert "except FileNotFoundError" in text
    assert "CleanupReconciliationOutcome.ABSENT" in text
    assert "self._reader._inventory(root, leaf_name, leaf, expected)" in text
    assert "CleanupReconciliationOutcome.PRESENT" in text
    assert text.count("CleanupReconciliationOutcome.CONFLICT") == 2


def test_local_inspection_revalidates_attempt_claim_target_and_artifacts() -> None:
    text = LOCAL.read_text(encoding="utf-8")
    section = text[text.index("if self._attempts(request.attempt_id) != attempt"):
                   text.index("return InspectedManifestHandoffSupervisorControlDirectoryCleanupReconciliation")]
    assert "current_claim" in section
    assert "current_retired" in section
    assert "current_artifacts" in section
    assert "self._now(claimed.claimed_at)" in section


def test_local_reconciliation_surface_has_no_mutation_primitive() -> None:
    text = LOCAL.read_text(encoding="utf-8")
    for forbidden in (
        "remove_control_directory(", "os.unlink", "os.rmdir", "os.mkdir",
        "os.rename", "os.replace", "os.fsync", "sqlalchemy", "INSERT ",
        "UPDATE ", "DELETE ", "SessionPrincipal", "create_app",
    ):
        assert forbidden not in text


def test_composition_secures_crashed_claim_as_unknown_before_inspection() -> None:
    text = APPLICATION.read_text(encoding="utf-8")
    start = text.index("def reconcile_control_directory_cleanup")
    unknown = text.index("UnknownManifestHandoffSupervisorControlDirectoryCleanupEffect(", start)
    persist = text.index("persist_control_directory_cleanup_physical_outcome(", start)
    inspect = text.index("inspect_control_directory_cleanup(request)", start)
    assert persist < unknown < inspect
    assert "type(secured) is not ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired" in text


def test_composition_inspects_once_then_persists_exact_classification() -> None:
    text = APPLICATION.read_text(encoding="utf-8")
    assert text.count("self._physical.inspect_control_directory_cleanup(request)") == 1
    inspect = text.index("self._physical.inspect_control_directory_cleanup(request)")
    persist = text.index("self._attempts.record_cleanup_reconciliation(")
    assert inspect < persist
    assert "inspected.request != request" in text
    assert "reconciled.outcome is not inspected.outcome" in text


def test_composition_has_no_physical_remove_loop_schema_or_wiring() -> None:
    text = APPLICATION.read_text(encoding="utf-8")
    tree = ast.parse(text)
    assert not any(isinstance(node, (ast.For, ast.While)) for node in ast.walk(tree))
    for forbidden in (
        "remove_control_directory(", "unlink", "rmdir", "sqlalchemy",
        "INSERT ", "UPDATE ", "DELETE ", "Path", "import os", "create_app",
        "SessionPrincipal", "WorkspaceId", "Permission",
    ):
        assert forbidden not in text


def test_roadmap_records_lq516_and_lq517() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-516 read-only supervisor control-directory cleanup reconciliation:" in roadmap
    assert "lq-516-read-only-supervisor-control-directory-cleanup-reconciliation.md" in roadmap
    assert "nächster Slice LQ-517" in roadmap
