import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "src/liquent_platform/persistence/manifest_handoff_supervisor_control_directory_cleanup_clearance.py"


def _text() -> str:
    return ADAPTER.read_text(encoding="utf-8")


def _methods() -> set[str]:
    tree = ast.parse(_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    return {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}


def test_adapter_implements_all_five_read_only_resolvers() -> None:
    assert {
        "resolve_control_directory_cleanup_management",
        "resolve_control_directory_cleanup_hold",
        "resolve_control_directory_cleanup_recovery",
        "resolve_control_directory_cleanup_references",
        "resolve_control_directory_cleanup_clearance",
    } <= _methods()


def test_management_reads_highest_actor_scope_revision_and_active_foundations() -> None:
    text = _text()
    assert "revision.actor_user_id=:actor AND revision.scope_id=:scope" in text
    assert "ORDER BY revision.sequence_number DESC LIMIT 1" in text
    assert "actor.status='active' AND scope.status='active'" in text
    assert "CleanupManagementStatus(row.status)" in text


def test_three_target_sources_are_separate_latest_directory_reads() -> None:
    text = _text()
    assert 'for kind in ("hold", "recovery", "reference")' in text
    assert "cleanup_{kind}_revisions" in text
    assert "WHERE directory_id=:directory ORDER BY sequence_number DESC LIMIT 1" in text
    assert "type(retired) is not RetiredManifestHandoffSupervisorControlDirectory" in text


def test_ids_times_dispositions_and_sequences_are_closed() -> None:
    text = _text()
    assert "self._sequence(row)" in text
    assert "row.sequence_number < 1" in text
    assert "CleanupClearanceDisposition(" in text
    assert "_utc(row.decided_at)" in text
    assert "_decode(row.revision_id)" in text


def test_clearance_is_found_only_by_request_attempt() -> None:
    text = _text()
    assert "WHERE attempt_id=:attempt" in text
    assert '{"attempt": _encode(request.attempt_id)}' in text
    assert "if row is None:\n            return None" in text
    assert "_decode(row.directory_id) != request.directory_id.value" in text
    assert "_decode(row.actor_user_id) != request.actor_user_id" in text


def test_aggregation_reloads_all_current_authorities() -> None:
    text = _text()
    for call in (
        "resolve_control_directory_cleanup_decision(",
        "resolve_control_directory_cleanup_management(",
        "resolve_control_directory_cleanup_hold(",
        "resolve_control_directory_cleanup_recovery(",
        "resolve_control_directory_cleanup_references(",
    ):
        assert call in text


def test_aggregation_requires_positive_current_dispositions() -> None:
    text = _text()
    assert "CleanupDisposition.ELIGIBLE" in text
    assert "CleanupManagementStatus.ACTIVE" in text
    assert text.count("CleanupClearanceDisposition.CLEAR") == 3


def test_all_bound_revision_ids_are_compared_to_current_values() -> None:
    text = _text()
    for column in (
        "decision_id", "management_revision_id", "hold_revision_id",
        "recovery_revision_id", "reference_revision_id",
    ):
        assert f"row.{column}" in text


def test_exactly_one_full_terminal_journal_is_required() -> None:
    text = _text()
    assert "self._writer(retired.handle_id)" in text
    assert "self._recovery(retired.handle_id)" in text
    assert "len(present) != 1" in text
    assert "ManifestHandoffSupervisorJournalState.TERMINAL_OBSERVED" in text
    assert "journal.terminal_observation_id is None or journal.result is None" in text
    assert "row.terminal_observation_id" in text


def test_detail_free_existing_unavailability_boundary_is_preserved() -> None:
    text = _text()
    assert "ManifestHandoffRegistryUnavailable" in text
    assert "except Exception:" in text
    assert 'connection.dialect.name not in ("postgresql", "sqlite")' in text
    assert "raise ManifestHandoffRegistryUnavailable from None" in text


def test_adapter_has_no_mutation_file_effect_wiring_or_session_authority() -> None:
    text = _text()
    for forbidden in (
        "INSERT ", "UPDATE ", "DELETE ", "Path", "open(", "unlink", "rmdir",
        "SessionPrincipal", "WorkspaceId", "research:read", "research:write",
        "create_app", "cleanup_control_directory(",
    ):
        assert forbidden not in text


def test_roadmap_records_lq498_and_lq499() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-498 persistent supervisor control-directory cleanup clearance adapter:" in roadmap
    assert "lq-498-persistent-supervisor-control-directory-cleanup-clearance-adapter.md" in roadmap
    assert "nächster Slice LQ-499" in roadmap
