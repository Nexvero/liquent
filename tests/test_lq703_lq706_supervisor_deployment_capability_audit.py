import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
COMPOSE = ROOT / "operations/compose/compose.yaml"
ENVIRONMENT = ROOT / "operations/compose/runtime.env.example"
PROCESS = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_process_composition.py"
LAUNCH = ROOT / "src/liquent_platform/transport/manifest_handoff_supervisor_launch_file.py"
CANDIDATE = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_candidate_composition.py"
ROADMAP = ROOT / "docs/technical-status-and-roadmap.md"


def _control_plane() -> str:
    text = COMPOSE.read_text(encoding="utf-8")
    return text.split("  control-plane:", 1)[1].split("  research-worker:", 1)[0]


def test_control_plane_has_no_partial_host_capability_activation() -> None:
    service = _control_plane()
    for forbidden in (
        "docker.sock", "supervisor-control", "group_add:",
        "user:", "manifest_handoff_supervisor",
    ):
        assert forbidden not in service


def test_runtime_example_documents_but_does_not_activate_atomic_settings() -> None:
    text = ENVIRONMENT.read_text(encoding="utf-8")
    names = (
        "MODE", "BACKEND_INSTANCE_ID", "DOCKER_SOCKET", "CONTROL_ROOT",
        "HOST_OWNER_UID", "READER_GID", "WRAPPER_UID", "WRAPPER_GID",
    )
    for suffix in names:
        assert f"# LIQUENT_MANIFEST_HANDOFF_SUPERVISOR_{suffix}=" in text


def test_launch_file_boundary_requires_parent_identity_and_private_directory() -> None:
    source = LAUNCH.read_text(encoding="utf-8")
    for required in (
        "host_owner_uid != os.geteuid()", "os.fchown(", "os.fchmod(",
        "0o640", "0o700", "os.O_NOFOLLOW", "os.link(",
    ):
        assert required in source


def test_followup_process_composition_binds_parent_launch_publisher() -> None:
    source = PROCESS.read_text(encoding="utf-8")
    assert source.count("AtomicLocalManifestHandoffSupervisorLaunchDocuments(") == 1
    assert "manifest_handoff_supervisor_launch_file" in source
    candidate = CANDIDATE.read_text(encoding="utf-8")
    tree = ast.parse(candidate)
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "compose_candidate_manifest_handoff_supervisor_graph"
    )
    assert any(arg.arg == "launch_documents" for arg in function.args.kwonlyargs)


def test_audit_records_raw_socket_and_path_identity_blockers() -> None:
    contract = (
        ROOT / "docs/lq-703-minimal-supervisor-deployment-capability-contract.md"
    ).read_text(encoding="utf-8")
    decision = (
        ROOT / "docs/lq-705-supervisor-deployment-preactivation-decision.md"
    ).read_text(encoding="utf-8")
    assert "roh gemounteter Docker-Daemon-Socket" in contract
    assert "demselben absoluten Pfad" in contract
    assert "read-only Socketmount" in decision
    assert "production_ready=true" in decision


def test_roadmap_records_complete_four_slice_audit() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")
    for number, name in (
        (703, "minimal-supervisor-deployment-capability-contract"),
        (704, "supervisor-host-capability-and-path-identity-evidence"),
        (705, "supervisor-deployment-preactivation-decision"),
        (706, "supervisor-deployment-capability-readiness-audit"),
    ):
        assert f"`docs/lq-{number}-{name}.md`" in roadmap
