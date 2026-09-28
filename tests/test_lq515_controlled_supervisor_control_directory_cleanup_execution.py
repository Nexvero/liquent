import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
APPLICATION = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_control_directory_cleanup_execution.py"


def _text() -> str:
    return APPLICATION.read_text(encoding="utf-8")


def test_composition_implements_only_high_level_cleanup_effect() -> None:
    tree = ast.parse(_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    methods = {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}
    assert "cleanup_control_directory" in methods
    assert not {"retry", "resume", "reconcile", "remove", "claim"} & methods


def test_exact_persistent_started_request_precedes_preflight() -> None:
    text = _text()
    section = text[text.index("def cleanup_control_directory"):text.index("def _complete_absent")]
    lookup = section.index("self._attempts.resolve_cleanup_attempt(request.attempt_id)")
    preflight = section.index("self._preflight.prepare_control_directory_cleanup(")
    assert lookup < preflight
    assert "type(current) is not CleanupManifestHandoffSupervisorControlDirectory" in section
    assert "if current != request" in section
    assert "if current is None:\n                return None" in section


def test_preflight_request_carries_only_attempt_and_directory() -> None:
    text = _text()
    assert "PreflightManifestHandoffSupervisorControlDirectoryCleanup(\n                    request.attempt_id, request.directory_id" in text
    assert "preflight.attempt_id != request.attempt_id" in text
    assert "preflight.directory_id != request.directory_id" in text


def test_absent_completes_without_claim_or_physical_effect() -> None:
    text = _text()
    section = text[text.index("def _complete_absent"):text.index("def _execute_once_or_unknown")]
    assert "complete_cleanup_attempt(" in section
    assert "CleanupOutcome.ALREADY_ABSENT" in section
    assert "claim_control_directory_cleanup_write" not in section
    assert "remove_control_directory" not in section
    assert "persist_control_directory_cleanup_physical_outcome" not in section


def test_prepared_is_claimed_before_exactly_one_physical_call() -> None:
    text = _text()
    claim = text.index("self._claims.claim_control_directory_cleanup_write(")
    physical = text.index("physical = self._execute_once_or_unknown(claimed)")
    persist = text.index("self._outcomes.persist_control_directory_cleanup_physical_outcome(")
    assert claim < physical < persist
    assert text.count("self._physical.remove_control_directory(claimed)") == 1
    assert "claimed.prepared != preflight" in text


def test_every_exception_or_invalid_result_after_claim_becomes_unknown() -> None:
    text = _text()
    section = text[text.index("def _execute_once_or_unknown"):text.index("def _same_claim")]
    assert "except Exception:\n            return self._unknown(claimed)" in section
    assert "if not self._same_claim(physical, claimed)" in section
    assert section.count("return self._unknown(claimed)") == 3
    assert "ManifestHandoffSupervisorControlDirectoryCleanupConflict" not in section


def test_outcome_store_is_called_once_and_result_is_strictly_validated() -> None:
    text = _text()
    assert text.count("self._outcomes.persist_control_directory_cleanup_physical_outcome(") == 1
    section = text[text.index("def _validated_persisted"):]
    assert "persisted.completed_at == physical.removed_at" in section
    assert "CleanupOutcome.REMOVED" in section
    assert "type(persisted) is ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired" in section
    assert "raise ManifestHandoffRegistryUnavailable" in section


def test_no_loop_retry_schema_file_primitive_or_wiring_is_added() -> None:
    text = _text()
    tree = ast.parse(text)
    assert not any(isinstance(node, (ast.For, ast.While)) for node in ast.walk(tree))
    for forbidden in (
        "sqlalchemy", "INSERT ", "UPDATE ", "DELETE ", "Path", "import os",
        "unlink", "rmdir", "mkdir", "SessionPrincipal", "WorkspaceId",
        "Permission", "create_app", "compose", "sleep(",
    ):
        assert forbidden not in text


def test_roadmap_records_lq515_and_lq516() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-515 controlled supervisor control-directory cleanup execution:" in roadmap
    assert "lq-515-controlled-supervisor-control-directory-cleanup-execution.md" in roadmap
    assert "nächster Slice LQ-516" in roadmap
