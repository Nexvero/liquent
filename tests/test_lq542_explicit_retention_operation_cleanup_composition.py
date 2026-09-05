import ast
from pathlib import Path


ROOT=Path(__file__).parents[1]
COMPOSITION=ROOT/"src/liquent_platform/application/manifest_handoff_supervisor_control_directory_cleanup_composition.py"


def _text(): return COMPOSITION.read_text(encoding="utf-8")


def test_composition_exposes_exactly_four_explicit_boundaries() -> None:
    tree=ast.parse(_text())
    cls=next(node for node in tree.body if isinstance(node,ast.ClassDef)
             and node.name=="ManifestHandoffSupervisorControlDirectoryCleanupComposition")
    slots=next(node for node in cls.body if isinstance(node,ast.Assign))
    assert ast.literal_eval(slots.value)==("retention_operation","clearance_creation","execution","reconciliation")


def test_retention_graph_shares_engine_and_directory_lookup() -> None:
    text=_text()
    assert "DatabaseManifestHandoffSupervisorCleanupRetentionPolicy(" in text
    assert "AuthoritativeManifestHandoffSupervisorCleanupRetentionEvaluation(" in text
    assert "DatabaseManifestHandoffSupervisorCleanupRetentionOperations(" in text
    assert "ControlledManifestHandoffSupervisorCleanupRetentionOperation(" in text
    assert "directories, evaluation, store" in text
    assert "directory_lookup=directories" in text


def test_generators_are_internal_and_closed_typed() -> None:
    text=_text()
    assert "policy_revision_generator=lambda:" in text
    assert "authority_revision_generator=lambda:" in text
    assert "decision_id_generator=lambda:" in text
    assert text.count("secrets.token_hex(32)")==3


def test_construction_does_not_execute_any_boundary() -> None:
    tree=ast.parse(_text())
    function=next(node for node in tree.body if isinstance(node,ast.FunctionDef)
                  and node.name=="compose_manifest_handoff_supervisor_control_directory_cleanup")
    calls={ast.unparse(node.func) for node in ast.walk(function) if isinstance(node,ast.Call)}
    for forbidden in ("retention_operation.execute","create_control_directory_cleanup_clearance",
                      "cleanup_control_directory","reconcile_control_directory_cleanup"):
        assert forbidden not in calls


def test_no_route_entrypoint_worker_or_disposal_effect() -> None:
    text=_text().lower()
    for forbidden in ("create_app", "route", "scheduler", "queue", "engine.dispose"):
        assert forbidden not in text


def test_roadmap_records_lq542_and_lq543() -> None:
    roadmap=(ROOT/"docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-542 explicit retention operation cleanup composition:" in roadmap
    assert "lq-542-explicit-retention-operation-cleanup-composition.md" in roadmap
    assert "nächster Slice LQ-543" in roadmap
