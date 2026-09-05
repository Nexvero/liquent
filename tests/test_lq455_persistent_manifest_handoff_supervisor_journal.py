import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "src/liquent_platform/persistence/manifest_handoff_supervisor_journal.py"


def _class() -> ast.ClassDef:
    tree = ast.parse(ADAPTER.read_text(encoding="utf-8"))
    return next(node for node in tree.body if isinstance(node, ast.ClassDef))


def test_adapter_implements_both_eight_method_journal_surfaces() -> None:
    methods = {node.name for node in _class().body if isinstance(node, ast.FunctionDef)}
    for capability in ("writer", "recovery"):
        assert {
            f"register_{capability}", f"commit_{capability}_launch",
            f"record_{capability}_gated", f"commit_{capability}_release",
            f"record_{capability}_running", f"request_{capability}_termination",
            f"record_{capability}_terminal", f"inspect_{capability}_journal",
        } <= methods


def test_adapter_is_constructively_bound_to_one_backend() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    assert '__slots__ = ("_engine", "_backend", "_clock")' in text
    assert "request.backend_instance_id != self._backend" in text
    assert "backend_selector" not in text and "backend_url" not in text


def test_registration_retry_compares_complete_immutable_binding() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    for field in (
        "handle_id", "backend_instance_id", "prepare_id", "launch_commit_id",
        "capability", "owner_id", "scope_id", "source_root", "target_root",
        "handoff_name",
    ):
        assert f"row.{field}" in text
    assert "ManifestHandoffSupervisorJournalConflict()" in text


def test_forward_state_machine_has_closed_predecessors() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    assert '"launch_committed": {ManifestHandoffSupervisorJournalState.PREPARE_REGISTERED}' in text
    assert '"prepared_gated": {ManifestHandoffSupervisorJournalState.LAUNCH_COMMITTED}' in text
    assert '"release_committed": {ManifestHandoffSupervisorJournalState.PREPARED_GATED}' in text
    assert '"running": {ManifestHandoffSupervisorJournalState.RELEASE_COMMITTED}' in text
    assert "TERMINAL_OBSERVED" not in text[text.index("def _allowed"):text.index("def inspect_writer_journal")]


def test_launch_identity_sequence_and_kind_are_idempotent() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    assert "job.launch_commit_id != values[\"transition\"]" in text
    assert "_TRANSITION_ID" in text and "_TRANSITION_KIND" in text
    assert '"sequence": len(history)+1' in text
    assert "row.sequence_number != index" in text


def test_terminal_payload_reconstructs_closed_domain_results() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    assert "CompletedManifestHandoffWriterProcess(" in text
    assert "CompletedManifestHandoffRecoveryProcess(" in text
    assert "ManifestHandoffWriterProcessKind(row.outcome_kind)" in text
    assert "ManifestHandoffRecoveryProcessKind(row.outcome_kind)" in text
    assert "ManifestHandoffFacts(row.manifest_sha256, row.file_count)" in text
    assert "_utc(request.result.ended_at)" in text


def test_adapter_has_no_process_authority_or_wiring_capability() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    for forbidden in ("subprocess", "Popen", "docker", "socket", "SessionPrincipal", "shell=True"):
        assert forbidden not in text
    assert "ManifestHandoffRegistryUnavailable" in text


def test_roadmap_records_lq455_and_next_service_contract() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-455 persistent manifest handoff supervisor journal:" in roadmap
    assert "lq-455-persistent-manifest-handoff-supervisor-journal.md" in roadmap
    assert "nächster Slice LQ-456" in roadmap
