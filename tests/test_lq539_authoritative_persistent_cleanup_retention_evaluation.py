import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
SERVICE = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_cleanup_retention_evaluation.py"


def _text(): return SERVICE.read_text(encoding="utf-8")


def test_service_accepts_lookup_and_external_clock_without_io_at_build() -> None:
    text = _text()
    assert "ManifestHandoffSupervisorCleanupRetentionPolicyLookup" in text
    cls = next(node for node in ast.parse(text).body if isinstance(node, ast.ClassDef))
    init = ast.unparse(next(node for node in cls.body if isinstance(node, ast.FunctionDef)
                            and node.name == "__init__"))
    assert "self._policies = policies" in init and "self._clock = clock" in init
    assert "self._clock()" not in init


def test_exact_types_and_retired_binding_are_required() -> None:
    text = _text()
    assert "type(request) is not EvaluateManifestHandoffSupervisorControlDirectoryRetention" in text
    assert "type(retired) is not RetiredManifestHandoffSupervisorControlDirectory" in text
    assert "request.directory_id != retired.directory_id" in text


def test_policy_is_resolved_once_before_clock_and_absence_is_neutral() -> None:
    text = _text()
    method = text[text.index("def evaluate_control_directory_retention"):]
    assert method.count("resolve_active_cleanup_retention_policy()") == 1
    assert method.index("resolve_active_cleanup_retention_policy()") < method.index("self._clock()")
    assert "if active is None:\n            return None" in method


def test_clock_is_utc_and_monotone_against_retirement_and_activation() -> None:
    text = _text()
    assert "evaluated_at.tzinfo is None" in text
    assert "evaluated_at < retired.retired_at" in text
    assert "evaluated_at < active.activated_at" in text


def test_threshold_is_retain_before_and_eligible_at_or_after() -> None:
    text = _text()
    assert "evaluated_at >= retired.retired_at + active.policy.minimum_retention" in text
    assert "CleanupDisposition.ELIGIBLE" in text
    assert "CleanupDisposition.RETAIN" in text


def test_result_binds_actual_policy_and_closed_data_class() -> None:
    text = _text()
    assert "SUPERVISOR_CONTROL_DIRECTORY" in text
    assert "active.policy.revision_id" in text
    assert "EvaluatedManifestHandoffSupervisorControlDirectoryRetention(" in text


def test_no_persistence_decision_clearance_or_file_effect() -> None:
    text = _text()
    for forbidden in ("sqlalchemy", "DecisionId", "bind_control_directory", "clearance",
                      "from pathlib", "open(", "unlink", "argparse"):
        assert forbidden not in text


def test_roadmap_records_lq539_and_lq540() -> None:
    roadmap=(ROOT/"docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-539 authoritative persistent supervisor cleanup retention evaluation:" in roadmap
    assert "lq-539-authoritative-persistent-supervisor-cleanup-retention-evaluation.md" in roadmap
    assert "nächster Slice LQ-540" in roadmap
