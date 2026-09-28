import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
OPERATOR = ROOT / "src/liquent_platform/operators/manifest_handoff_supervisor_control_directory_cleanup.py"


def _text() -> str:
    return OPERATOR.read_text(encoding="utf-8")


def _function(name: str) -> ast.FunctionDef:
    return next(
        node for node in ast.parse(_text()).body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


def test_private_reader_is_descriptor_bound_owner_only_and_bounded() -> None:
    text = _text()
    section = ast.unparse(_function("_private_bytes"))
    for required in (
        "os.O_NOFOLLOW", "os.O_CLOEXEC", "os.fstat", "status.st_uid != os.geteuid()",
        "status.st_nlink != 1", "(256, 384)", "status.st_size > maximum",
    ):
        assert required in section
    assert "os.read" in section


def test_requests_are_exact_and_reject_duplicate_or_open_fields() -> None:
    text = _text()
    assert "object_pairs_hook=_pairs" in text
    assert 'fields: set[str]' in text
    assert "set(value) != fields" in text
    assert '_request(path, {"actor_user_id", "directory_id"})' in text
    assert '_request(path, {"attempt_id", "directory_id"})' in text
    for forbidden in ('"allow"', '"force"', '"role"', '"permission"', '"clearance_id"'):
        assert forbidden not in text


def test_configuration_is_explicit_private_and_readiness_gated() -> None:
    text = _text()
    assert "database_url_file" in text
    assert "backend_instance_id_file" in text
    assert "control_root_file" in text
    assert "DatabaseReadinessProbe(engine).check().ready" in text
    assert "compose_manifest_handoff_supervisor_control_directory_cleanup(" in text
    for forbidden in ("os.environ", "getenv", "upgrade_to_head", "create_all"):
        assert forbidden not in text


def test_root_is_absolute_existing_owner_private_and_symlink_free() -> None:
    section = ast.unparse(_function("_private_root"))
    assert "path.is_absolute()" in section
    assert "path.resolve(strict=True)" in section
    assert "resolved != path" in section
    assert "status.st_uid != os.geteuid()" in section
    assert "stat.S_IMODE(status.st_mode) != 448" in section
    for forbidden in ("mkdir", "chmod", "chown"):
        assert forbidden not in section


def test_execute_generates_one_attempt_then_clearance_then_execution() -> None:
    section = ast.unparse(_function("execute_one"))
    assert section.count("secrets.token_hex(32)") == 1
    clearance = section.index("create_control_directory_cleanup_clearance")
    execution = section.index("cleanup_control_directory")
    assert clearance < execution
    assert "if clearance is None" in section
    assert "if type(clearance) is ManifestHandoffSupervisorControlDirectoryCleanupConflict" in section
    assert not any(isinstance(node, (ast.For, ast.While)) for node in ast.walk(_function("execute_one")))


def test_unknown_is_returned_without_automatic_reconciliation() -> None:
    section = ast.unparse(_function("execute_one"))
    assert "reconciliation_required" in section
    assert "reconcile_control_directory_cleanup" not in section
    assert section.count("cleanup_control_directory(request)") == 1


def test_reconcile_has_one_read_only_call_and_no_execute_surface() -> None:
    section = ast.unparse(_function("reconcile_one"))
    assert section.count("reconcile_control_directory_cleanup(request)") == 1
    for forbidden in (
        "SessionPrincipal", "create_control_directory_cleanup_clearance",
        "cleanup_control_directory", "secrets", "token_hex",
    ):
        assert forbidden not in section


def test_operator_owns_and_always_disposes_one_engine() -> None:
    section = ast.unparse(_function("run_operator"))
    assert section.count("build_engine(database_url)") == 1
    assert "finally:" in section
    assert "engine.dispose()" in section


def test_cli_has_two_commands_four_file_options_and_closed_errors() -> None:
    text = _text()
    assert 'for name in ("execute", "reconcile")' in text
    for option in (
        "--database-url-file", "--backend-instance-id-file",
        "--control-root-file", "--request",
    ):
        assert option in text
    assert "SupervisorControlDirectoryCleanupOperatorInputRejected.code, 2" in text
    assert "SupervisorControlDirectoryCleanupOperatorUnavailable.code, 4" in text


def test_packaged_as_one_separate_console_entry_point() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    expected = (
        'liquent-supervisor-control-directory-cleanup = '
        '"liquent_platform.operators.manifest_handoff_supervisor_control_directory_cleanup:main"'
    )
    assert project.count(expected) == 1


def test_no_discovery_batch_scheduler_or_automatic_wiring() -> None:
    text = _text().lower()
    for forbidden in (
        "list_control", "find_control", "all_director", "for directory",
        "while true", "scheduler", "cron", "create_app", "lifespan", "worker",
    ):
        assert forbidden not in text


def test_roadmap_records_lq519_and_lq520() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-519 owner-controlled single supervisor control-directory cleanup operator:" in roadmap
    assert "lq-519-owner-controlled-single-supervisor-control-directory-cleanup-operator.md" in roadmap
    assert "nächster Slice LQ-520" in roadmap
