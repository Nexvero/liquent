import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "src/liquent_platform/persistence/manifest_handoff_supervisor_cleanup_retention_operation.py"


def _text() -> str:
    return ADAPTER.read_text(encoding="utf-8")


def _method(name: str) -> ast.FunctionDef:
    tree = ast.parse(_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    return next(node for node in cls.body if isinstance(node, ast.FunctionDef)
                and node.name == name)


def test_adapter_implements_only_closed_operation_binding_surface() -> None:
    text = _text()
    assert "class DatabaseManifestHandoffSupervisorCleanupRetentionOperations:" in text
    assert "def bind_control_directory_retention_decision(self, command):" in text
    assert "BindManifestHandoffSupervisorControlDirectoryRetentionDecision" in text
    for forbidden in ("SessionPrincipal", "WorkspaceId", "Permission", '"allow"'):
        assert forbidden not in text


def test_retry_precedes_decision_collision_and_binds_first_writer_directory() -> None:
    section = ast.unparse(_method("bind_control_directory_retention_decision"))
    retry = section.index("existing = self._one(connection, _OPERATION")
    collision = section.index("collided = self._one(connection, _DECISION")
    directory = section.index("directory = self._one(connection, _DIRECTORY")
    assert retry < collision < directory
    assert "bound.evaluation.request.directory_id == evaluation.request.directory_id" in section


def test_new_operation_requires_current_exact_retired_value() -> None:
    text = _text()
    section = ast.unparse(_method("bind_control_directory_retention_decision"))
    assert "DatabaseManifestHandoffSupervisorControlDirectories._lifecycle" in section
    assert "type(retired) is not RetiredManifestHandoffSupervisorControlDirectory" in section
    assert "retired != evaluation.retired" in section
    assert "return None" in section


def test_decision_sequence_and_clock_are_monotone() -> None:
    section = ast.unparse(_method("bind_control_directory_retention_decision"))
    assert "sequence = 1 if latest is None else latest.sequence_number + 1" in section
    assert "bound_at = _utc(self._clock())" in section
    assert "bound_at < evaluation.evaluated_at" in section
    assert "evaluation.evaluated_at" in section


def test_decision_and_operation_inserts_are_ordered_in_one_transaction() -> None:
    text = _text()
    decision = text.index("INSERT INTO manifest_handoff_supervisor_control_cleanup_decisions")
    operation = text.index("INSERT INTO manifest_handoff_supervisor_cleanup_retention_operations")
    assert decision < operation
    write = ast.unparse(_method("_write"))
    assert "with self._engine.begin() as connection" in write
    assert "return action(connection)" in write
    assert "commit" not in text.lower()


def test_reconstruction_checks_operation_and_decision_independently() -> None:
    text = _text()
    assert "operation.policy_revision_id AS operation_policy_revision_id" in text
    assert "operation.disposition AS operation_disposition" in text
    bound = ast.unparse(_method("_bound"))
    assert "row.operation_policy_revision_id" in bound
    assert "row.policy_revision_id" in bound
    assert "row.operation_disposition" in bound
    assert "row.disposition" in bound
    assert "bound_at < evaluation.evaluated_at" in bound


def test_postgres_locks_are_fixed_and_other_dialects_fail_closed() -> None:
    text = _text()
    lock = text[text.index("_LOCK ="):text.index("_DIRECTORY =")]
    for table in (
        "manifest_handoff_supervisor_control_directories",
        "manifest_handoff_supervisor_control_cleanup_decisions",
        "manifest_handoff_supervisor_cleanup_retention_operations",
    ):
        assert table in lock
    write = ast.unparse(_method("_write"))
    assert "connection.dialect.name == 'postgresql'" in write
    assert "connection.dialect.name != 'sqlite'" in write


def test_no_policy_file_follow_on_update_or_delete_power() -> None:
    text = _text()
    for forbidden in (
        "from pathlib", "import os", "UPDATE ", "DELETE ",
        "create_control_directory_cleanup_clearance", "start_cleanup_attempt",
        "retire_control_directory", "create_app", "argparse",
    ):
        assert forbidden not in text


def test_head_inventory_and_roadmap_remain_synchronized() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    bundle = (ROOT / "tools/operational_release_bundle.py").read_text(encoding="utf-8")
    assert "**42 lineare Migrationen**, Head\n  `20260826_0042`" in roadmap
    assert "EXPECTED_MIGRATION_COUNT = 42" in bundle
    assert "**71 Console Entry Points**, **70 Operatorimplementierungs-" in roadmap


def test_roadmap_records_lq529_and_lq530() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-529 atomic persistent supervisor cleanup retention operation store:" in roadmap
    assert "lq-529-atomic-persistent-supervisor-cleanup-retention-operation-store.md" in roadmap
    assert "nächster Slice LQ-530" in roadmap
