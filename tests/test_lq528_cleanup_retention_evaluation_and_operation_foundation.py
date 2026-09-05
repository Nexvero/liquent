import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
DOMAIN = ROOT / "src/liquent_platform/identity/manifest_handoff_supervisor_cleanup_retention.py"
PORTS = ROOT / "src/liquent_platform/identity/ports.py"
MIGRATION = ROOT / "src/liquent_platform/persistence/alembic/versions/20260826_0041_cleanup_retention_operation_bindings.py"


def test_operation_id_and_request_are_repr_free_and_minimal() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    assert "class ManifestHandoffSupervisorCleanupRetentionOperationId:" in text
    assert "value: str = field(repr=False)" in text
    section = text[text.index("class EvaluateManifestHandoffSupervisorControlDirectoryRetention"):
                   text.index("class EvaluatedManifestHandoffSupervisorControlDirectoryRetention")]
    assert "operation_id:" in section and "directory_id:" in section
    for forbidden in ("disposition", "policy_revision", "allow", "role", "Path"):
        assert forbidden not in section


def test_evaluation_is_retired_policy_data_class_and_time_bound() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    assert 'SUPERVISOR_CONTROL_DIRECTORY = "supervisor_control_directory"' in text
    section = text[text.index("class EvaluatedManifestHandoffSupervisorControlDirectoryRetention"):
                   text.index("class BindManifestHandoffSupervisorControlDirectoryRetentionDecision")]
    for field in ("request:", "retired:", "data_class:", "policy_revision_id:",
                  "disposition:", "evaluated_at:"):
        assert field in section
    assert "self.request.directory_id == self.retired.directory_id" in section
    assert "self.evaluated_at < self.retired.retired_at" in section


def test_bound_result_revalidates_every_evaluation_decision_fact() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    section = text[text.index("class BoundManifestHandoffSupervisorControlDirectoryRetentionDecision"):
                   text.index("class ManifestHandoffSupervisorCleanupRetentionOperationConflict")]
    for comparison in (
        "self.decision.retired == self.evaluation.retired",
        "self.decision.policy_revision_id",
        "self.decision.disposition == self.evaluation.disposition",
        "self.decision.decided_at == self.evaluation.evaluated_at",
    ):
        assert comparison in section
    assert "return self.evaluation.request.operation_id" in section


def test_conflict_is_fieldless_and_domain_has_no_runtime_power() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    tree = ast.parse(text)
    conflict = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                    and node.name == "ManifestHandoffSupervisorCleanupRetentionOperationConflict")
    assert not [node for node in conflict.body if isinstance(node, ast.AnnAssign)]
    for forbidden in ("sqlalchemy", "argparse", "SessionPrincipal", "open(", "unlink"):
        assert forbidden not in text


def test_ports_are_exact_read_only_evaluation_and_binding_surfaces() -> None:
    text = PORTS.read_text(encoding="utf-8")
    assert "class ManifestHandoffSupervisorCleanupRetentionPolicyEvaluation(Protocol):" in text
    assert "def evaluate_control_directory_retention(" in text
    assert "class ManifestHandoffSupervisorCleanupRetentionOperationStore(Protocol):" in text
    assert "def bind_control_directory_retention_decision(" in text


def test_revision_is_linear_empty_and_creates_one_operation_table() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert 'revision: str = "20260826_0041"' in text
    assert 'down_revision: str | Sequence[str] | None = "20260826_0040"' in text
    assert text.count("op.create_table(") == 1
    assert '"manifest_handoff_supervisor_cleanup_retention_operations"' in text
    for forbidden in ("INSERT ", "UPDATE ", "DELETE ", "op.bulk_insert"):
        assert forbidden not in text


def test_operation_primary_decision_unique_and_composite_fk_are_closed() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert 'sa.PrimaryKeyConstraint(\n            "operation_id"' in text
    assert 'sa.UniqueConstraint(\n            "decision_id"' in text
    assert '["decision_id", "directory_id"]' in text
    assert 'f"{_DECISIONS}.decision_id"' in text
    assert 'f"{_DECISIONS}.directory_id"' in text


def test_persisted_values_and_time_order_are_constrained() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert "length(operation_id)>0" in text
    assert "length(policy_revision_id)>0" in text
    assert "data_class='supervisor_control_directory'" in text
    assert "disposition IN ('retain','eligible')" in text
    assert "bound_at>=evaluated_at" in text


def test_current_head_inventory_and_roadmap_are_synchronized() -> None:
    gate = (ROOT / "tests/test_persistence_migration_gate.py").read_text(encoding="utf-8")
    bundle = (ROOT / "tools/operational_release_bundle.py").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    migrations = list((ROOT / "src/liquent_platform/persistence/alembic/versions").glob("*.py"))
    assert len(migrations) == 42
    assert 'expected_head() == "20260826_0042"' in gate
    assert "EXPECTED_MIGRATION_COUNT = 42" in bundle
    assert "**42 lineare Migrationen**, Head\n  `20260826_0042`" in roadmap


def test_roadmap_records_lq528_and_lq529() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-528 supervisor cleanup retention evaluation and operation foundation:" in roadmap
    assert "lq-528-supervisor-cleanup-retention-evaluation-and-operation-foundation.md" in roadmap
    assert "nächster Slice LQ-529" in roadmap
