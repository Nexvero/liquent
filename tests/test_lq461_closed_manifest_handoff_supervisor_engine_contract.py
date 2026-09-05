import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
DOMAIN = ROOT / "src/liquent_platform/identity/manifest_handoff_supervisor_engine.py"
PORTS = ROOT / "src/liquent_platform/identity/ports.py"


def _classes(path: Path) -> dict[str, ast.ClassDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}


def _methods(node: ast.ClassDef) -> list[str]:
    return [item.name for item in node.body if isinstance(item, ast.FunctionDef)]


def test_profiles_and_engine_states_are_closed() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    assert text.count('= "writer"') == 1 and text.count('= "recovery"') == 1
    for state in ("created", "running", "exited", "dead"):
        assert f'= "{state}"' in text


def test_create_is_digest_bound_and_returns_runtime_identity() -> None:
    classes = _classes(DOMAIN)
    create = ast.unparse(classes["CreateManifestHandoffSupervisorContainer"])
    created = ast.unparse(classes["CreatedManifestHandoffSupervisorContainer"])
    for name in ("handle_id", "creation_id", "control_directory_id", "image_digest", "profile"):
        assert name in create
    assert "runtime_container_id" in created


def test_requests_expose_no_free_process_or_infrastructure_parameters() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    for forbidden in ("command:", "args:", "environment:", "timeout:", "socket:",
                      "host:", "path:", "pid:", "restart:", "allow:", "SessionPrincipal"):
        assert forbidden not in text


def test_engine_port_has_exactly_five_closed_operations() -> None:
    engine = _classes(PORTS)["ManifestHandoffSupervisorEngine"]
    assert _methods(engine) == ["create", "inspect", "start", "wait_terminal", "terminate"]


def test_terminate_acknowledgement_is_separate_from_terminal_observation() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    assert "AcceptedManifestHandoffSupervisorTermination" in text
    accepted = ast.unparse(_classes(DOMAIN)["AcceptedManifestHandoffSupervisorTermination"])
    assert "state" not in accepted and "terminal" not in accepted
    assert "ManifestHandoffSupervisorTerminateId" in accepted


def test_contract_has_detail_free_conflict_and_no_implementation() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    assert "class ManifestHandoffSupervisorEngineConflict" in text
    for forbidden in ("import docker", "subprocess", "requests", "urllib", "sqlalchemy", "open("):
        assert forbidden not in text


def test_roadmap_records_lq461_and_next_adapter() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-461 closed manifest handoff supervisor engine contract:" in roadmap
    assert "lq-461-closed-manifest-handoff-supervisor-engine-contract.md" in roadmap
    assert "nächster Slice LQ-462" in roadmap
