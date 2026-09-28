import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
SERVICE = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_release_service.py"


def _text() -> str:
    return SERVICE.read_text(encoding="utf-8")


def _methods() -> set[str]:
    tree = ast.parse(_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    return {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}


def test_service_exposes_both_profile_specific_release_operations() -> None:
    assert {"release_writer", "release_recovery"} <= _methods()


def test_only_prepared_release_committed_and_running_are_accepted() -> None:
    text = _text()
    for state in ("PREPARED_GATED", "RELEASE_COMMITTED", "RUNNING"):
        assert f"ManifestHandoffSupervisorJournalState.{state}" in text
    assert "journal.state not in" in text


def test_persistent_bindings_and_ready_precede_release_commit() -> None:
    text = _text()
    runtime = text.index("runtime = self._runtime.resolve_runtime")
    gate = text.index("gate = self._gates.resolve_gate")
    ready = text.index("ready_record = self._artifact")
    commit = text.index("journal = commit_release(")
    assert runtime < gate < ready < commit


def test_release_commit_precedes_token_and_token_precedes_consumed() -> None:
    text = _text()
    commit_call = text.index("journal = commit_release(")
    publish_call = text.index("released = self._publish_release")
    assert commit_call < publish_call
    helper = text[text.index("def _publish_release"):]
    token = helper.index("self._publisher.publish")
    token_record = helper.index("record_release_token")
    consumed = helper.index("publish_consumed")
    consumed_record = helper.index("record_release_consumed")
    assert token < token_record < consumed < consumed_record


def test_engine_running_precedes_journal_running_and_executor() -> None:
    text = _text()
    inspect = text.index("observation = self._engine.inspect")
    running = text.index("journal = record_running(")
    execute = text.index("executed = execute(execution)")
    assert inspect < running < execute
    assert "ManifestHandoffSupervisorEngineState.RUNNING" in text


def test_running_retry_reconstructs_without_publish_or_execute_branch() -> None:
    text = _text()
    assert "if already_running:" in text
    assert "released = self._reconstruct_released" in text
    assert "else:\n                released = self._publish_release" in text
    assert "if not already_running:" in text
    assert "retry = record_running" in text


def test_release_and_running_identities_are_compared() -> None:
    text = _text()
    assert "journal.release_id != command.release_id" in text
    assert "command.running_observation_id" in text
    assert "token.token_artifact_id != command.token_artifact_id" in text


def test_conflicts_and_technical_failures_remain_detail_free() -> None:
    text = _text()
    assert "_CONFLICTS" in text
    assert "ManifestHandoffSupervisorServiceConflict()" in text
    assert "ManifestHandoffRegistryUnavailable" in text


def test_no_authority_terminal_termination_cleanup_or_wiring() -> None:
    text = _text()
    for forbidden in ("SessionPrincipal", "UserId", "WorkspaceId", "Permission",
            "allow", "publish_terminal", "record_writer_terminal", "terminate(",
            "UPDATE ", "DELETE ", "create_app", "compose"):
        assert forbidden not in text


def test_roadmap_records_lq476_and_next_inspect_slice() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-476 persistent supervisor release orchestration:" in roadmap
    assert "lq-476-persistent-supervisor-release-orchestration.md" in roadmap
    assert "nächster Slice LQ-477" in roadmap
