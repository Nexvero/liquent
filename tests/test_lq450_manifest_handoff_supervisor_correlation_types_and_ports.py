import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
DOMAIN = ROOT / "src/liquent_platform/identity/manifest_handoff_supervisor_correlation.py"
PORTS = ROOT / "src/liquent_platform/identity/ports.py"


def _classes(path: Path) -> dict[str, ast.ClassDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}


def _methods(node: ast.ClassDef) -> list[str]:
    return [item.name for item in node.body if isinstance(item, ast.FunctionDef)]


def test_closed_identity_and_backend_types_exist() -> None:
    classes = _classes(DOMAIN)
    assert {
        "ManifestHandoffSupervisorBackendInstanceId",
        "ManifestHandoffSupervisorPrepareId",
        "ManifestHandoffSupervisorReleaseId",
        "ManifestHandoffSupervisorTerminateId",
        "ManifestHandoffSupervisorTerminalObservationId",
        "ManifestHandoffSupervisorBackendStatus",
        "ManifestHandoffSupervisorBackend",
    } <= classes.keys()
    text = DOMAIN.read_text(encoding="utf-8")
    assert 'ACTIVE = "active"' in text and 'INACTIVE = "inactive"' in text
    assert text.count("value: str = field(repr=False)") == 5


def test_writer_and_recovery_preparations_are_not_nullable_union_requests() -> None:
    classes = _classes(DOMAIN)
    writer = classes["ReserveManifestHandoffWriterPreparation"]
    recovery = classes["ReserveManifestHandoffRecoveryPreparation"]
    writer_text = ast.unparse(writer)
    recovery_text = ast.unparse(recovery)
    assert "ManifestHandoffExecutionClaimId" in writer_text
    assert "ManifestHandoffExecutionOwnerId" in writer_text
    assert "ManifestHandoffRecoveryClaimId" not in writer_text
    assert "ManifestHandoffRecoveryClaimId" in recovery_text
    assert "ManifestHandoffRecoveryOwnerId" in recovery_text
    assert "ManifestHandoffExecutionClaimId" not in recovery_text


def test_operation_requests_have_only_stable_id_and_handle() -> None:
    classes = _classes(DOMAIN)
    for name, identity in (
        ("RecordManifestHandoffSupervisorRelease", "release_id"),
        ("RecordManifestHandoffSupervisorTermination", "terminate_id"),
        ("RecordManifestHandoffSupervisorTerminalObservation", "terminal_observation_id"),
    ):
        fields = {
            item.target.id
            for item in classes[name].body
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
        }
        assert fields == {identity, "handle_id"}


def test_backend_store_and_lookup_ports_are_minimal_and_separate() -> None:
    classes = _classes(PORTS)
    assert _methods(classes["CurrentManifestHandoffSupervisorBackend"]) == ["resolve"]
    assert _methods(classes["ManifestHandoffSupervisorCorrelationStore"]) == [
        "reserve_writer",
        "reserve_recovery",
        "bind_handle",
        "record_release",
        "record_termination",
        "record_terminal_observation",
    ]
    assert _methods(classes["ManifestHandoffSupervisorCorrelationLookup"]) == [
        "resolve_preparation",
        "resolve_handle",
        "resolve_release",
        "resolve_termination",
        "resolve_terminal_observation",
    ]


def test_ports_accept_no_authority_process_status_or_clock_parameters() -> None:
    classes = _classes(PORTS)
    forbidden = {
        "principal", "actor", "role", "allow", "authority", "command", "args",
        "env", "cwd", "shell", "timeout", "signal", "status", "now", "clock",
    }
    for class_name in (
        "CurrentManifestHandoffSupervisorBackend",
        "ManifestHandoffSupervisorCorrelationStore",
        "ManifestHandoffSupervisorCorrelationLookup",
    ):
        for item in classes[class_name].body:
            if isinstance(item, ast.FunctionDef):
                parameters = {arg.arg for arg in item.args.args}
                assert not forbidden & parameters


def test_domain_has_no_process_persistence_or_transport_imports() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    for forbidden in (
        "subprocess", "sqlalchemy", "alembic", "socket", "docker", "SessionPrincipal",
    ):
        assert forbidden not in text
    assert "class ManifestHandoffSupervisorCorrelationConflict:" in text


def test_roadmap_records_lq450_and_next_adapter_slice() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-450 manifest handoff supervisor correlation types and ports:" in roadmap
    assert "lq-450-manifest-handoff-supervisor-correlation-types-and-ports.md" in roadmap
    assert "nächster Slice LQ-451" in roadmap
