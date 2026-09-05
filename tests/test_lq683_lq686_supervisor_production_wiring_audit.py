import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
SETTINGS = ROOT / "src/liquent_platform/configuration.py"
MAIN = ROOT / "src/liquent_platform/transport/http/main.py"
APP = ROOT / "src/liquent_platform/transport/http/app.py"
CANDIDATE = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_candidate_composition.py"
COMPATIBILITY = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_composition.py"
COMPOSE = ROOT / "operations/compose/compose.yaml"
ROADMAP = ROOT / "docs/technical-status-and-roadmap.md"


def _function(path: Path, name: str) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(
        item for item in ast.walk(tree)
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and item.name == name
    )
    return ast.unparse(node)


def test_settings_group_is_atomic_but_cannot_select_the_candidate_alone() -> None:
    text = SETTINGS.read_text(encoding="utf-8")
    assert 'extra="forbid"' in text
    for required in (
        "manifest_handoff_supervisor_mode",
        "manifest_handoff_supervisor_backend_instance_id",
        "manifest_handoff_supervisor_docker_socket",
        "manifest_handoff_supervisor_control_root",
        "manifest_handoff_supervisor_wrapper_uid",
    ):
        assert required in text
    assert "manifest handoff supervisor settings must be provided together" in text
    main = MAIN.read_text(encoding="utf-8")
    assert "if settings.manifest_handoff_supervisor_enabled:" in main
    assert "compose_manifest_handoff_supervisor_candidate_process" in main


def test_entrypoint_and_appfactory_do_not_own_a_partial_candidate() -> None:
    build = _function(MAIN, "build_app")
    factory = _function(APP, "create_app")
    for forbidden in (
        "compose_candidate_manifest_handoff_supervisor_graph",
        "LocalDockerEngineHttpClient",
        "supervisor_client",
        "supervisor_graph",
    ):
        assert forbidden not in build
        assert forbidden not in factory


def test_lifecycle_has_claimed_close_while_deployment_remains_closed() -> None:
    lifespan = _function(APP, "lifespan")
    assert "mark_stopping" in lifespan
    assert "manifest_handoff_supervisor_process.close" in lifespan
    assert "oidc_http_client.close" in lifespan
    assert "engine.dispose" in lifespan
    compose = COMPOSE.read_text(encoding="utf-8")
    assert "docker.sock" not in compose
    assert "supervisor-control" not in compose


def test_deployment_has_no_capability_only_or_settings_only_activation() -> None:
    text = COMPOSE.read_text(encoding="utf-8")
    control_plane = text.split("  control-plane:", 1)[1].split(
        "  research-worker:", 1
    )[0]
    assert "docker.sock" not in control_plane
    assert "/run/liquent/control" not in control_plane
    assert "liquent-supervisor-writer-wrapper" not in text
    assert "liquent-supervisor-recovery-wrapper" not in text


def test_candidate_and_compatibility_graphs_remain_exclusive_and_closed() -> None:
    candidate = CANDIDATE.read_text(encoding="utf-8")
    compatibility = COMPATIBILITY.read_text(encoding="utf-8")
    assert "production_ready: bool = field(default=False, init=False)" in candidate
    assert "capability_executor," in compatibility
    assert "capability_outcomes," in compatibility
    assert "executor=capability_executor" in compatibility
    assert "compose_persistent_manifest_handoff_supervisor_service" not in candidate


def test_audit_documents_and_roadmap_are_complete() -> None:
    expected = (
        "lq-683-all-or-nothing-supervisor-production-wiring-contract.md",
        "lq-684-supervisor-production-ownership-readiness-shutdown-evidence.md",
        "lq-685-exclusive-supervisor-production-selection-decision.md",
        "lq-686-supervisor-production-wiring-readiness-audit.md",
    )
    roadmap = ROADMAP.read_text(encoding="utf-8")
    for name in expected:
        text = (ROOT / "docs" / name).read_text(encoding="utf-8")
        assert "Production" in text
        assert f"`docs/{name}`" in roadmap
