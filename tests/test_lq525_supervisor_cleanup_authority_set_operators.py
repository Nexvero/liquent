import ast
from pathlib import Path
import re


ROOT = Path(__file__).parents[1]
OPERATOR = ROOT / "src/liquent_platform/operators/manifest_handoff_supervisor_cleanup_authority.py"


def _text() -> str:
    return OPERATOR.read_text(encoding="utf-8")


def _function(name: str) -> ast.FunctionDef:
    return next(
        node for node in ast.parse(_text()).body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


def test_three_separate_entry_points_share_one_internal_module() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for boundary in ("bootstrap", "lifecycle", "recovery"):
        expected = (
            f'liquent-supervisor-cleanup-authority-{boundary} = '
            f'"liquent_platform.operators.manifest_handoff_supervisor_cleanup_authority:{boundary}_main"'
        )
        assert project.count(expected) == 1


def test_all_boundaries_have_four_fixed_domain_commands() -> None:
    text = _text()
    assert '("management", "hold", "recovery", "reference")' in text
    for domain in ("management", "hold", "recovery", "reference"):
        assert f'"{domain}": _Domain(' in text
    assert '"source"' not in text
    assert '"allow"' not in text
    assert '"role"' not in text


def test_request_shapes_are_exact_and_distinct() -> None:
    text = _text()
    assert '{"bootstrap_id", "target_user_id", "scope_id"}' in text
    lifecycle = ast.unparse(_function("load_lifecycle_request"))
    for field in (
        "actor_user_id", "change_id", "target_user_id", "scope_id",
        "expected_revision_id", "intent",
    ):
        assert field in lifecycle
    recovery = ast.unparse(_function("load_recovery_request"))
    assert "actor_user_id" not in recovery
    assert "SessionPrincipal" not in recovery


def test_lifecycle_principal_does_not_carry_authority() -> None:
    lifecycle = ast.unparse(_function("load_lifecycle_request"))
    assert "SessionPrincipal(UserId(value['actor_user_id']))" in lifecycle
    assert "ManifestHandoffSupervisorCleanupMutationAuthorityLifecycleIntent" in lifecycle


def test_each_domain_calls_explicit_existing_adapter_methods() -> None:
    text = _text()
    for action in ("bootstrap", "change", "recover"):
        for domain in ("management", "hold", "recovery", "reference"):
            assert f"{action}_cleanup_{domain}_mutation_authority" in text
    assert "getattr(store" not in text


def test_readiness_result_binding_and_engine_disposal_are_closed() -> None:
    text = _text()
    assert "DatabaseReadinessProbe(engine).check().ready" in text
    assert "type(result.revision_id) is not selected.revision_type" in text
    assert "result.scope_id != command.scope_id" in text
    main = ast.unparse(_function("_main"))
    assert main.count("build_engine(database_url)") == 1
    assert "finally:" in main and "engine.dispose()" in main


def test_private_inputs_and_atomic_result_reuse_hardened_boundaries() -> None:
    text = _text()
    assert "_one_line(args.database_url_file)" in text
    assert "_request(path, fields)" in text
    assert "_write_result(args.result_file, result)" in text
    for forbidden in ("os.environ", "getenv", "create_all", "upgrade_to_head"):
        assert forbidden not in text


def test_closed_outcomes_and_no_follow_on_mutation_exist() -> None:
    text = _text()
    assert '_emit("rejected")' in text
    assert '_emit("applied")' in text
    assert '"operation_id"' in text and '"revision_id"' in text
    for forbidden in (
        "change_control_directory_cleanup_management",
        "create_control_directory_cleanup_clearance",
        "cleanup_control_directory(", "retire_control_directory",
        "record_cleanup_decision",
    ):
        assert forbidden not in text


def test_package_inventory_is_synchronized_fail_closed() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    scripts = re.findall(r"^liquent-[a-z0-9-]+\s*=", project, re.MULTILINE)
    operators = list((ROOT / "src/liquent_platform/operators").glob("*.py"))
    bundle = (ROOT / "tools/operational_release_bundle.py").read_text(encoding="utf-8")
    assert len(scripts) == 71
    assert len(operators) == 71
    assert "EXPECTED_ENTRY_POINT_COUNT = 71" in bundle
    assert "EXPECTED_OPERATOR_FILE_COUNT = 71" in bundle
    assert "lq-524-owner-controlled-supervisor-cleanup-authority-and-source-revision-operator-contract.md" in bundle
    assert "lq-525-owner-controlled-supervisor-cleanup-authority-set-operators.md" in bundle


def test_roadmap_records_lq525_and_lq526() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-525 owner-controlled supervisor cleanup authority-set operators:" in roadmap
    assert "lq-525-owner-controlled-supervisor-cleanup-authority-set-operators.md" in roadmap
    assert "nächster Slice LQ-526" in roadmap
