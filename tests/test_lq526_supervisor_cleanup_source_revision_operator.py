import ast
from pathlib import Path
import re


ROOT = Path(__file__).parents[1]
OPERATOR = ROOT / "src/liquent_platform/operators/manifest_handoff_supervisor_cleanup_source_revision.py"


def _text() -> str:
    return OPERATOR.read_text(encoding="utf-8")


def _function(name: str) -> ast.FunctionDef:
    return next(
        node for node in ast.parse(_text()).body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


def test_one_separate_entry_point_has_four_fixed_commands() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    expected = (
        'liquent-supervisor-cleanup-source-revision = '
        '"liquent_platform.operators.manifest_handoff_supervisor_cleanup_source_revision:main"'
    )
    assert project.count(expected) == 1
    assert '("management", "hold", "recovery", "reference")' in _text()


def test_management_and_directory_requests_are_exact_and_distinct() -> None:
    management = ast.unparse(_function("load_management_request"))
    for field in (
        "actor_user_id", "change_id", "target_user_id", "scope_id",
        "expected_revision_id", "status",
    ):
        assert field in management
    target = ast.unparse(_function("_target_request"))
    assert "target_user_id" not in target
    assert "scope_id" not in target
    assert "directory_id" in target and "disposition" in target


def test_only_expected_revision_accepts_explicit_json_null() -> None:
    request = ast.unparse(_function("_request"))
    assert "key == 'expected_revision_id' and item is None" in request
    assert "type(item) is not str" in request
    expected = ast.unparse(_function("_expected"))
    assert "if value is None" in expected
    assert "return None" in expected


def test_principal_identifies_actor_without_allow_or_role() -> None:
    text = _text()
    assert text.count("SessionPrincipal(UserId(value[") == 2
    for forbidden in ('"source"', '"allow"', '"role"', '"permission"'):
        assert forbidden not in text


def test_four_explicit_adapter_methods_are_used() -> None:
    text = _text()
    for method in (
        "change_control_directory_cleanup_management",
        "change_control_directory_cleanup_hold",
        "change_control_directory_cleanup_recovery",
        "change_control_directory_cleanup_references",
    ):
        assert method in text
    assert "getattr(store" not in text


def test_results_are_rebound_to_operation_and_target() -> None:
    management = ast.unparse(_function("_management_result"))
    assert "result.change_id != command.change_id" in management
    assert "result.authority.actor_user_id != command.target_user_id" in management
    assert "result.authority.scope_id != command.scope_id" in management
    target = ast.unparse(_function("_target_result"))
    assert "result.change_id != command.change_id" in target
    assert "result.decision.retired.directory_id != command.directory_id" in target


def test_readiness_private_files_and_engine_disposal_are_closed() -> None:
    text = _text()
    assert "DatabaseReadinessProbe(engine).check().ready" in text
    assert "_private_text(path)" in text
    assert "_one_line(args.database_url_file)" in text
    assert "_write_result(args.result_file, result)" in text
    main = ast.unparse(_function("main"))
    assert main.count("build_engine(database_url)") == 1
    assert "finally:" in main and "engine.dispose()" in main


def test_outcomes_are_closed_and_follow_on_effects_absent() -> None:
    text = _text()
    assert '_emit("applied")' in text and '_emit("rejected")' in text
    assert "supervisor_cleanup_source_revision_operator_unavailable" in text
    for forbidden in (
        "bootstrap_cleanup_", "recover_cleanup_", "mutation_authority(principal",
        "create_control_directory_cleanup_clearance", "record_cleanup_decision",
        "retire_control_directory", "cleanup_control_directory(", "create_app",
    ):
        assert forbidden not in text


def test_package_inventory_and_contract_are_synchronized() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    scripts = re.findall(r"^liquent-[a-z0-9-]+\s*=", project, re.MULTILINE)
    operators = list((ROOT / "src/liquent_platform/operators").glob("*.py"))
    bundle = (ROOT / "tools/operational_release_bundle.py").read_text(encoding="utf-8")
    assert len(scripts) == 71
    assert len(operators) == 71
    assert "EXPECTED_ENTRY_POINT_COUNT = 71" in bundle
    assert "EXPECTED_OPERATOR_FILE_COUNT = 71" in bundle
    assert "lq-526-owner-controlled-supervisor-cleanup-source-revision-operator.md" in bundle


def test_roadmap_records_lq526_and_lq527() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-526 owner-controlled supervisor cleanup source revision operator:" in roadmap
    assert "lq-526-owner-controlled-supervisor-cleanup-source-revision-operator.md" in roadmap
    assert "nächster Slice LQ-527" in roadmap
