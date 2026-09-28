import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "src/liquent_platform/persistence/manifest_handoff_supervisor_control_directory_cleanup.py"


def _text() -> str:
    return ADAPTER.read_text(encoding="utf-8")


def _methods() -> set[str]:
    cls = next(node for node in ast.parse(_text()).body if isinstance(node, ast.ClassDef))
    return {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}


def test_adapter_has_decision_attempt_transition_and_lookup_methods() -> None:
    assert {
        "record_cleanup_decision", "resolve_control_directory_cleanup_decision",
        "start_cleanup_attempt", "record_cleanup_outcome_unknown",
        "complete_cleanup_attempt", "record_cleanup_reconciliation",
        "resolve_cleanup_attempt",
    } <= _methods()


def test_decision_requires_current_exact_retired_and_appends_sequence() -> None:
    text = _text()
    assert "DatabaseManifestHandoffSupervisorControlDirectories._lifecycle(directory)" in text
    assert "type(lifecycle) is not RetiredManifestHandoffSupervisorControlDirectory" in text
    assert "if lifecycle != decision.retired:" in text
    assert "sequence = 1 if latest is None else latest.sequence_number + 1" in text
    assert "INSERT INTO manifest_handoff_supervisor_control_cleanup_decisions" in text


def test_decision_lookup_is_latest_and_reconstructs_full_value() -> None:
    text = _text()
    assert "ORDER BY decision.sequence_number DESC LIMIT 1" in text
    assert "ManifestHandoffSupervisorControlDirectoryRetentionDecisionId(" in text
    assert "ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId(" in text
    assert "ManifestHandoffSupervisorControlDirectoryCleanupDisposition(row.disposition)" in text


def test_start_rechecks_current_exact_eligible_decision_before_insert() -> None:
    text = _text()
    start = text[text.index("def start_cleanup_attempt"):text.index("def record_cleanup_outcome_unknown")]
    assert "current = self._resolved_decision(transaction, values)" in start
    assert "current != decision" in start
    assert "CleanupDisposition.ELIGIBLE" in start
    assert start.index("current =") < start.index("INSERT INTO manifest_handoff_supervisor_control_cleanup_attempts")


def test_start_retry_binds_attempt_directory_actor_and_decision() -> None:
    text = _text()
    assert "self._attempt(existing)" in text
    assert "_decode(row.directory_id) == request.directory_id.value" in text
    assert "_decode(row.actor_user_id) == request.actor_user_id" in text
    assert "_decode(row.decision_id) == decision.decision_id.value" in text


def test_only_claim_safe_forward_transitions_exist() -> None:
    text = _text()
    assert 'expected="write_claimed", target="outcome_unknown"' in text
    assert "outcome is not ManifestHandoffSupervisorControlDirectoryCleanupOutcome.ALREADY_ABSENT" in text
    assert 'expected="started", target="completed"' in text
    assert "persist_control_directory_cleanup_physical_outcome" in text
    assert "state='completed',outcome='removed',completed_at=:at" in text
    assert 'expected="outcome_unknown", target="reconciled"' in text
    for forbidden in ("reopen", "reset", "reactivate", "DELETE "):
        assert forbidden not in text


def test_attempt_reconstruction_checks_matrix_and_monotone_times() -> None:
    text = _text()
    for state in ("started", "write_claimed", "outcome_unknown", "completed", "reconciled"):
        assert f'row.state == "{state}"' in text
    assert "value is not None for value in" in text
    assert "started_at < _utc(row.decision_decided_at)" in text
    assert "_utc(row.unknown_at) < claimed.claimed_at" in text
    assert "completed_at < lower" in text
    assert "_utc(row.reconciled_at) < unknown_at" in text


def test_postgres_locks_sqlite_and_detail_free_boundary_exist() -> None:
    text = _text()
    for table in (
        "identity_users", "manifest_handoff_supervisor_control_directories",
        "manifest_handoff_supervisor_control_cleanup_decisions",
        "manifest_handoff_supervisor_control_cleanup_attempts",
    ):
        assert table in text[text.index("_LOCK ="):text.index("_DIRECTORY =")]
    assert 'connection.dialect.name == "postgresql"' in text
    assert 'connection.dialect.name != "sqlite"' in text
    assert "ManifestHandoffRegistryUnavailable" in text


def test_no_file_authority_delete_execution_port_or_wiring() -> None:
    text = _text()
    for forbidden in (
        "Path", "os.", "open(", "unlink", "rmdir", "SessionPrincipal",
        "WorkspaceId", "Permission", "allow", "create_app", "compose_",
        "cleanup_control_directory(",
    ):
        assert forbidden not in text


def test_roadmap_records_lq494_and_lq495() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-494 persistent supervisor control-directory cleanup registry adapter:" in roadmap
    assert "lq-494-persistent-supervisor-control-directory-cleanup-registry-adapter.md" in roadmap
    assert "nächster Slice LQ-495" in roadmap
