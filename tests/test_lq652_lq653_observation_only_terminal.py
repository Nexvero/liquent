import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_observation_terminal.py"


def class_text():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    return ast.unparse(cls)


def test_terminal_service_exposes_writer_and_recovery_completion():
    text = class_text()
    assert "def complete_writer" in text
    assert "def complete_recovery" in text


def test_direct_terminal_is_recorded_before_engine_observation_and_journal_terminal():
    text = class_text()
    direct = text.index("self._recorder.record_terminal(gate)")
    engine = text.index("self._engine.inspect")
    journal = text.index("journal = record_terminal(transition_type(")
    assert direct < engine < journal


def test_absent_terminal_and_running_engine_are_neutral_without_journal_transition():
    text = class_text()
    assert "if terminal is None:" in text
    assert "if observation.state is ManifestHandoffSupervisorEngineState.RUNNING:" in text
    transition = text.index("journal = record_terminal(transition_type(")
    assert text.index("if terminal is None:") < transition
    assert text.index("if observation.state is ManifestHandoffSupervisorEngineState.RUNNING:") < transition


def test_journal_terminal_requires_direct_engine_exited_or_dead():
    text = class_text()
    assert "ManifestHandoffSupervisorEngineState.EXITED" in SOURCE.read_text(encoding="utf-8")
    assert "ManifestHandoffSupervisorEngineState.DEAD" in SOURCE.read_text(encoding="utf-8")
    assert "observation.state not in _ENGINE_TERMINAL" in text


def test_outcome_profile_handle_and_persisted_result_are_compared():
    text = class_text()
    assert "type(outcome) is not outcome_type" in text
    assert "outcome.handle_id != command.handle_id" in text
    assert "journal.result != outcome" in text


def test_parent_terminal_has_no_publish_executor_outcome_port_or_wait():
    text = SOURCE.read_text(encoding="utf-8")
    for forbidden in ("publish_terminal", "execute_writer", "execute_recovery",
                      "inspect_writer_outcome", "inspect_recovery_outcome",
                      "wait_terminal", "await_release"):
        assert forbidden not in text


def test_no_authority_schema_cli_or_wiring_added():
    text = SOURCE.read_text(encoding="utf-8")
    for forbidden in ("SessionPrincipal", "Permission", "allow", "sqlalchemy",
                      "argparse", "create_app", "compose", "subprocess"):
        assert forbidden not in text
