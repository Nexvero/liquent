import ast
from pathlib import Path
import re


ROOT = Path(__file__).parents[1]
OPERATOR = ROOT / "src/liquent_platform/operators/manifest_handoff_supervisor_cleanup_retention_policy.py"


def _text(): return OPERATOR.read_text(encoding="utf-8")


def test_four_fixed_entry_points_are_registered() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for name, function in (("policy-bootstrap", "bootstrap_main"),
                           ("policy-change", "policy_main"),
                           ("authority-lifecycle", "lifecycle_main"),
                           ("authority-recovery", "recovery_main")):
        assert f'liquent-supervisor-cleanup-retention-{name} = ' in project
        assert f':{function}"' in project


def test_request_shapes_are_exact_and_recovery_is_principal_free() -> None:
    text = _text()
    assert '{"bootstrap_id", "target_user_id", "minimum_retention_seconds"}' in text
    assert '{"actor_user_id", "change_id", "expected_revision_id", "intent", "minimum_retention_seconds"}' in text
    assert '{"actor_user_id", "change_id", "target_user_id", "expected_revision_id", "intent"}' in text
    recovery = text[text.index("def load_recovery_request"):text.index("def _store")]
    assert "actor_user_id" not in recovery and "SessionPrincipal" not in recovery


def test_clock_and_revision_generators_are_internal() -> None:
    text = _text()
    assert "datetime.now(timezone.utc)" in text
    assert text.count("secrets.token_hex(32)") == 2
    assert "policy_revision_generator=" in text
    assert "authority_revision_generator=" in text


def test_each_boundary_calls_only_its_persistent_method() -> None:
    text = _text()
    for method in ("bootstrap_cleanup_retention_policy", "change_cleanup_retention_policy(",
                   "change_cleanup_retention_policy_authority", "recover_cleanup_retention_policy_authority"):
        assert method in text
    assert "getattr(" not in text


def test_private_files_readiness_result_and_disposal_are_closed() -> None:
    text = _text()
    assert "_read_private(args.database_url_file)" in text
    assert "_write_result(args.result_file, result)" in text
    assert "DatabaseReadinessProbe(engine).check().ready" in text
    assert "finally:" in text and "engine.dispose()" in text
    for forbidden in ("os.environ", "getenv", "input(", "create_all", "upgrade_to_head"):
        assert forbidden not in text


def test_outcomes_and_deactivation_payload_are_closed() -> None:
    text = _text()
    assert "{\"outcome\":\"rejected\"}" in text
    assert "{\"outcome\":\"applied\"}" in text
    assert "{\"error\":\"operator_unavailable\"}" in text
    assert 'if result.active_policy is not None:' in text
    assert 'payload["revision_id"]' in text


def test_inventory_is_synchronized() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    scripts = re.findall(r"^liquent-[a-z0-9-]+\s*=", project, re.MULTILINE)
    operators = list((ROOT / "src/liquent_platform/operators").glob("*.py"))
    bundle = (ROOT / "tools/operational_release_bundle.py").read_text(encoding="utf-8")
    assert len(scripts) == 71 and len(operators) == 71
    assert "EXPECTED_ENTRY_POINT_COUNT = 71" in bundle
    assert "EXPECTED_OPERATOR_FILE_COUNT = 71" in bundle
    assert "lq-537-owner-controlled-supervisor-cleanup-retention-policy-operator-contract.md" in bundle


def test_no_follow_on_cleanup_or_wiring() -> None:
    text = _text()
    for forbidden in ("record_cleanup_decision", "create_control_directory_cleanup_clearance",
                      "cleanup_control_directory(", "create_app"):
        assert forbidden not in text


def test_roadmap_records_lq538_and_lq539() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-538 owner-controlled supervisor cleanup retention policy operators:" in roadmap
    assert "lq-538-owner-controlled-supervisor-cleanup-retention-policy-operators.md" in roadmap
    assert "nächster Slice LQ-539" in roadmap
