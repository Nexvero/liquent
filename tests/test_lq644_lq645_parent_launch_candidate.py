import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_parent_launch.py"


def source():
    return SOURCE.read_text(encoding="utf-8")


def classes():
    return {node.name: node for node in ast.parse(source()).body
            if isinstance(node, ast.ClassDef)}


def class_text(name):
    return ast.unparse(classes()[name])


def test_launch_prefix_exposes_profiles_and_stops_before_ready():
    text = class_text("PersistentManifestHandoffSupervisorParentLaunchPrefix")
    assert "def launch_writer" in text and "def launch_recovery" in text
    for forbidden in ("publish_ready", "record_ready", "record_gated",
                      "publish_consumed", "execute_writer", "execute_recovery"):
        assert forbidden not in text


def test_registration_commit_create_bind_gate_start_order_is_preserved():
    text = class_text("PersistentManifestHandoffSupervisorParentLaunchPrefix")
    register = text.index("journal = register(command.registration)")
    commit = text.index("journal = commit_launch(")
    resolve = text.index("self._runtime.resolve_runtime")
    create = text.index("self._create_and_bind(command, profile)")
    gate = text.index("self._gates.bind_gate")
    inspect = text.index("self._engine.inspect")
    start = text.index("self._engine.start")
    assert register < commit < resolve < create < gate < inspect < start


def test_create_carries_complete_launch_anchor_before_runtime_binding():
    text = class_text("PersistentManifestHandoffSupervisorParentLaunchPrefix")
    helper = text[text.index("def _create_and_bind"):]
    create = helper.index("self._engine.create")
    bind = helper.index("self._runtime.bind_runtime")
    assert create < bind
    assert "command.launch_document_id" in helper
    assert "command.launch_document_digest" in helper


def test_prefix_result_requires_direct_engine_running():
    text = class_text("PersistentManifestHandoffSupervisorParentLaunchPrefix")
    running = text.index("observation.state is not ManifestHandoffSupervisorEngineState.RUNNING")
    result = text.index("LaunchedManifestHandoffSupervisorParentPrefix(")
    assert running < result


def test_candidate_composes_only_prefix_then_direct_ready_completion():
    text = class_text("CandidateObservationOnlyManifestHandoffSupervisorPrepareService")
    assert "self._launch.launch_writer" in text
    assert "self._completion.prepare_writer" in text
    assert "self._launch.launch_recovery" in text
    assert "self._completion.prepare_recovery" in text
    assert text.index("prefix = launch(command)") < text.index("return complete(command)")


def test_candidate_never_completes_after_absence_or_conflict():
    text = class_text("CandidateObservationOnlyManifestHandoffSupervisorPrepareService")
    assert "prefix is None" in text
    assert "type(prefix) is ManifestHandoffSupervisorServiceConflict" in text
    assert text.index("return prefix") < text.index("return complete(command)")


def test_parallel_candidate_has_no_release_execution_terminal_or_wiring():
    text = source()
    for forbidden in ("await_release", "publish_consumed", "execute_writer",
                      "execute_recovery", "publish_terminal", "create_app", "compose"):
        assert forbidden not in text


def test_no_actor_authority_or_free_process_configuration():
    text = source()
    for forbidden in ("SessionPrincipal", "Permission", "allow", "command:",
                      "args:", "environment:", "subprocess", "argparse"):
        assert forbidden not in text
