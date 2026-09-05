import ast
from pathlib import Path

ROOT=Path(__file__).parents[1]
SERVICE=ROOT/"src/liquent_platform/application/manifest_handoff_supervisor_terminate_service.py"
def _text(): return SERVICE.read_text(encoding="utf-8")
def _methods():
    cls=next(n for n in ast.parse(_text()).body if isinstance(n,ast.ClassDef))
    return {n.name for n in cls.body if isinstance(n,ast.FunctionDef)}

def test_profile_specific_terminate_methods():
    assert {"terminate_writer","terminate_recovery"} <= _methods()

def test_only_ready_visible_nonterminal_states_are_accepted():
    text=_text()
    for state in ("PREPARED_GATED","RELEASE_COMMITTED","RUNNING","TERMINATION_REQUESTED","TERMINAL_OBSERVED"):
        assert f"ManifestHandoffSupervisorJournalState.{state}" in text
    assert "LAUNCH_COMMITTED" not in text

def test_termination_journal_precedes_engine_signal():
    text=_text()
    durable=text.index("journal = request_termination(")
    signal=text.index("accepted = self._engine.terminate")
    wait=text.index("observation = self._engine.wait_terminal")
    assert durable < signal < wait

def test_pre_release_unknown_and_released_wait_are_separate():
    text=_text()
    assert "if released is None:" in text
    assert "ManifestHandoffWriterProcessKind.OUTCOME_UNKNOWN" in text
    assert "ManifestHandoffRecoveryProcessKind.OUTCOME_UNKNOWN" in text
    assert "executed = wait_outcome(inspection_type(execution))" in text
    assert ".execute_writer" not in text and ".execute_recovery" not in text

def test_envelope_facts_verify_and_terminal_journal_follow_engine():
    text=_text()
    wait=text.index("observation = self._engine.wait_terminal")
    envelope=text.index("self._wrapper.publish_terminal")
    facts=text.index("self._artifacts.record_terminal_envelope")
    verify=text.index("self._verify_envelope")
    journal=text.index("terminal = record_terminal")
    assert wait < envelope < facts < verify < journal

def test_stable_terminate_and_terminal_ids_are_used():
    text=_text()
    assert "command.terminate_id" in text
    assert "journal.terminate_id != command.terminate_id" in text
    assert "gate.terminal_observation_id" in text
    assert "accepted.terminate_id != command.terminate_id" in text

def test_no_authority_free_signal_cleanup_schema_or_wiring():
    text=_text()
    for forbidden in ("SessionPrincipal","UserId","WorkspaceId","Permission","allow",
            "signal=","timeout=","UPDATE ","DELETE ","create_app","compose"):
        assert forbidden not in text

def test_roadmap_records_lq479_and_lq480():
    roadmap=(ROOT/"docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-479 persistent supervisor terminate orchestration:" in roadmap
    assert "lq-479-persistent-supervisor-terminate-orchestration.md" in roadmap
    assert "nächster Slice LQ-480" in roadmap
