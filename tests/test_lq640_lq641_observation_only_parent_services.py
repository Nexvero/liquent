import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_observation_parent.py"


def text():
    return SOURCE.read_text(encoding="utf-8")


def classes():
    tree = ast.parse(text())
    return {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}


def methods(name):
    return {node.name for node in classes()[name].body if isinstance(node, ast.FunctionDef)}


def test_parallel_prepare_has_profile_entries_but_no_launch_or_publish_surface():
    name = "ObservationOnlyManifestHandoffSupervisorPrepareCompletion"
    assert {"prepare_writer", "prepare_recovery"} <= methods(name)
    source = ast.unparse(classes()[name])
    for forbidden in (".create(", ".start(", "publish_ready", "publish_consumed",
                      "execute_writer", "execute_recovery"):
        assert forbidden not in source


def test_prepare_requires_running_then_direct_ready_before_gated_transition():
    source = ast.unparse(classes()["ObservationOnlyManifestHandoffSupervisorPrepareCompletion"])
    running = source.index("ManifestHandoffSupervisorEngineState.RUNNING")
    ready = source.index("self._recorder.record_ready(gate)")
    gated = source.index("record_gated(RecordManifestHandoffSupervisorGated")
    assert running < ready < gated


def test_prepare_absent_direct_ready_is_neutral_without_transition():
    source = ast.unparse(classes()["ObservationOnlyManifestHandoffSupervisorPrepareCompletion"])
    assert "if ready is None:" in source
    assert source.index("if ready is None") < source.index("record_gated(")


def test_parallel_release_exposes_profiles_without_executor_or_consumed_publish():
    name = "ObservationOnlyManifestHandoffSupervisorReleaseService"
    assert {"release_writer", "release_recovery"} <= methods(name)
    source = ast.unparse(classes()[name])
    for forbidden in ("execute_writer", "execute_recovery", "publish_consumed",
                      "await_release", "publish_terminal"):
        assert forbidden not in source


def test_release_orders_commit_token_direct_consumed_engine_and_running():
    source = ast.unparse(classes()["ObservationOnlyManifestHandoffSupervisorReleaseService"])
    commit = source.index("commit_release(CommitManifestHandoffSupervisorGateRelease")
    token = source.index("self._ensure_token(command, gate)")
    consumed = source.index("self._recorder.record_consumed(gate, command.release_id)")
    inspect = source.index("self._engine.inspect")
    running = source.index("record_running(RecordManifestHandoffSupervisorRunning")
    assert commit < token < consumed < inspect < running


def test_absent_consumed_never_records_running():
    source = ast.unparse(classes()["ObservationOnlyManifestHandoffSupervisorReleaseService"])
    assert "if consumed is None:" in source
    assert source.index("if consumed is None") < source.index("record_running(")


def test_only_release_token_is_parent_published():
    source = ast.unparse(classes()["ObservationOnlyManifestHandoffSupervisorReleaseService"])
    assert source.count("self._publisher.publish(") == 1
    assert "ManifestHandoffSupervisorReleaseTokenDocument" in source
    assert "ReadyDocument" not in source
    assert "ReleaseConsumedDocument" not in source


def test_no_actor_authority_schema_cli_or_wiring_is_added():
    source = text()
    for forbidden in ("SessionPrincipal", "UserId", "WorkspaceId", "Permission",
                      "allow", "sqlalchemy", "argparse", "create_app", "compose"):
        assert forbidden not in source
