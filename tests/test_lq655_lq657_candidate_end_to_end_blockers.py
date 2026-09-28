import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
CLIENT = ROOT / "src/liquent_platform/transport/local_docker_engine_http_client.py"
CHILD = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_child_process.py"
LOADER = ROOT / "src/liquent_platform/transport/manifest_handoff_supervisor_launch_loader.py"
CANDIDATE = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_candidate_composition.py"
COMPATIBILITY = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_composition.py"
MAIN = ROOT / "src/liquent_platform/transport/http/main.py"
COMPOSE = ROOT / "operations/compose/compose.yaml"


def function_text(path: Path, name: str) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(item for item in ast.walk(tree)
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and item.name == name)
    return ast.unparse(node)


def test_create_specification_has_no_child_expectation_channel():
    text = function_text(CLIENT, "_create_specification")
    assert "'Entrypoint'" in text
    assert "'Labels'" in text
    assert "'HostConfig'" in text
    assert "'Env'" not in text
    assert "ManifestHandoffSupervisorLaunchDocumentExpectation" not in text


def test_loader_requires_external_expectation_and_checks_all_anchor_facts():
    text = function_text(LOADER, "load")
    assert "type(expectation) is not ManifestHandoffSupervisorLaunchDocumentExpectation" in text
    for fact in ("digest", "document_id", "creation_id", "handle_id",
                 "control_directory_id", "image_digest", "profile"):
        assert fact in text


def test_engine_mounts_are_now_profile_closed_while_wiring_remains_blocked():
    text = function_text(CLIENT, "_mounts")
    assert ":/run/liquent/control:rw" in text
    assert ":/run/liquent/launch/launch-binding.json:ro" in text
    assert ":/run/liquent/source:ro" in text
    assert ":/run/liquent/target:rw" in text
    assert ":/run/liquent/target:ro" in text
    assert ":/run/liquent/source:rw" not in text


def test_candidate_is_an_object_graph_not_a_process_entrypoint():
    candidate = CANDIDATE.read_text(encoding="utf-8")
    child = CHILD.read_text(encoding="utf-8")
    assert "OneShotManifestHandoffSupervisorChildProcess(" in candidate
    for forbidden in ('if __name__ == "__main__"', "def main(", "argparse", "sys.argv"):
        assert forbidden not in candidate
        assert forbidden not in child


def test_production_files_do_not_select_candidate_or_wrapper_service():
    for path in (MAIN, COMPOSE):
        text = path.read_text(encoding="utf-8")
        assert "compose_candidate_manifest_handoff_supervisor_graph" not in text
        assert "manifest-handoff-supervisor-wrapper" not in text


def test_compatibility_graph_still_owns_parent_executor_and_outcomes():
    text = COMPATIBILITY.read_text(encoding="utf-8")
    assert "capability_executor," in text
    assert "capability_outcomes," in text
    assert "executor=capability_executor" in text


def test_candidate_readiness_claim_remains_closed():
    text = CANDIDATE.read_text(encoding="utf-8")
    assert "terminal_observation_complete: bool = field(default=True, init=False)" in text
    assert "production_ready: bool = field(default=False, init=False)" in text
