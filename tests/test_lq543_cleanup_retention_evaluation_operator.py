from pathlib import Path
import re


ROOT=Path(__file__).parents[1]
OPERATOR=ROOT/"src/liquent_platform/operators/manifest_handoff_supervisor_cleanup_retention_policy.py"
COMPOSITION=ROOT/"src/liquent_platform/application/manifest_handoff_supervisor_control_directory_cleanup_composition.py"


def test_retention_entry_point_is_fixed_and_unique() -> None:
    project=(ROOT/"pyproject.toml").read_text(encoding="utf-8")
    entry=('liquent-supervisor-cleanup-retention-evaluate = '
           '"liquent_platform.operators.manifest_handoff_supervisor_cleanup_retention_policy:retention_main"')
    assert project.count(entry)==1


def test_request_is_exact_minimal_and_has_no_policy_claim() -> None:
    text=OPERATOR.read_text(encoding="utf-8")
    section=text[text.index("def load_retention_request"):text.index("def _store")]
    assert '{"operation_id", "directory_id"}' in section
    for forbidden in ("disposition", "policy_revision", "decision_id", "allow", "minimum_retention"):
        assert forbidden not in section


def test_operator_reuses_shared_retention_factory() -> None:
    operator=OPERATOR.read_text(encoding="utf-8")
    composition=COMPOSITION.read_text(encoding="utf-8")
    assert "compose_manifest_handoff_supervisor_cleanup_retention_operation(" in operator
    assert "def compose_manifest_handoff_supervisor_cleanup_retention_operation(" in composition
    assert ").execute(command)" in operator


def test_result_is_closed_and_has_no_follow_on_action() -> None:
    text=OPERATOR.read_text(encoding="utf-8")
    for field in ("operation_id", "directory_id", "decision_id", "policy_revision_id", "disposition"):
        assert f'"{field}"' in text
    for forbidden in ("create_control_directory_cleanup_clearance", "cleanup_control_directory(",
                      "record_cleanup_decision", "retire_control_directory"):
        assert forbidden not in text


def test_private_readiness_result_and_disposal_are_reused() -> None:
    text=OPERATOR.read_text(encoding="utf-8")
    assert "DatabaseReadinessProbe(engine).check().ready" in text
    assert "_read_private(args.database_url_file)" in text
    assert "_write_result(args.result_file, result)" in text
    assert "engine.dispose()" in text


def test_inventory_is_synchronized() -> None:
    project=(ROOT/"pyproject.toml").read_text(encoding="utf-8")
    scripts=re.findall(r"^liquent-[a-z0-9-]+\s*=",project,re.MULTILINE)
    bundle=(ROOT/"tools/operational_release_bundle.py").read_text(encoding="utf-8")
    assert len(scripts)==71
    assert "EXPECTED_ENTRY_POINT_COUNT = 71" in bundle


def test_roadmap_records_lq543_and_lq544() -> None:
    roadmap=(ROOT/"docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-543 owner-controlled supervisor cleanup retention evaluation operator:" in roadmap
    assert "lq-543-owner-controlled-supervisor-cleanup-retention-evaluation-operator.md" in roadmap
    assert "nächster Slice LQ-544" in roadmap
