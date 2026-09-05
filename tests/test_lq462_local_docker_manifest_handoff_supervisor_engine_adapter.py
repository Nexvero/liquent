import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "src/liquent_platform/transport/manifest_handoff_supervisor_docker_engine.py"


def _methods(class_name: str) -> list[str]:
    tree = ast.parse(ADAPTER.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    return [node.name for node in cls.body if isinstance(node, ast.FunctionDef)]


def test_adapter_implements_exact_engine_surface_without_remove() -> None:
    methods = _methods("LocalDockerManifestHandoffSupervisorEngine")
    for method in ("create", "inspect", "start", "wait_terminal", "terminate"):
        assert method in methods
    assert not {"remove", "prune", "restart"} & set(methods)


def test_create_reconciles_creation_before_one_create() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    find = text.index("self._client.find")
    create = text.index("self._client.create")
    assert find < create
    assert "if len(found) > 1" in text
    assert "if found:" in text and "return self._created(request, found[0])" in text


def test_closed_security_profile_is_adapter_owned() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    for value in ('"network_mode": "none"', '"restart_policy": "no"',
                  '"auto_remove": False', '"readonly_rootfs": True',
                  '"cap_drop": ("ALL",)', '"privileged": False',
                  '"pid_mode": "private"'):
        assert value in text
    assert "request.network" not in text and "request.command" not in text


def test_create_and_inspect_enforce_configured_profile_digest() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    assert "request.image_digest != self._images[request.profile]" in text
    assert "observation.image_digest != self._images[observation.profile]" in text
    assert "raw.get(\"labels\") == self._labels(request)" in text


def test_start_is_allowed_only_from_created_and_wait_only_terminal() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    assert "observation.state is not ManifestHandoffSupervisorEngineState.CREATED" in text
    assert "ManifestHandoffSupervisorEngineState.EXITED" in text
    assert "ManifestHandoffSupervisorEngineState.DEAD" in text
    assert "raise ManifestHandoffRegistryUnavailable" in text


def test_termination_uses_same_container_and_never_claims_terminal() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    assert "self._client.stop(request.runtime_container_id.value)" in text
    assert "self._client.kill(request.runtime_container_id.value)" in text
    accepted = ast.unparse(next(node for node in ast.parse(text).body
        if isinstance(node, ast.ClassDef) and node.name == "LocalDockerManifestHandoffSupervisorEngine"))
    assert "remove(" not in accepted and "prune(" not in accepted


def test_no_shell_sdk_authority_or_wiring_is_added() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    for forbidden in ("subprocess", "Popen", "import docker", "SessionPrincipal",
                      "allow:", "sqlalchemy", "argparse"):
        assert forbidden not in text


def test_roadmap_records_lq462_and_next_file_contract() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-462 local docker manifest handoff supervisor engine adapter:" in roadmap
    assert "lq-462-local-docker-manifest-handoff-supervisor-engine-adapter.md" in roadmap
    assert "nächster Slice LQ-463" in roadmap
