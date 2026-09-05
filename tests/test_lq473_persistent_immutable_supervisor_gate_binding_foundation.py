import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
MIGRATION = ROOT / "src/liquent_platform/persistence/alembic/versions/20260825_0033_manifest_handoff_supervisor_gate_bindings.py"
PORTS = ROOT / "src/liquent_platform/identity/ports.py"


def _classes(path: Path) -> dict[str, ast.ClassDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}


def _methods(node: ast.ClassDef) -> list[str]:
    return [item.name for item in node.body if isinstance(item, ast.FunctionDef)]


def test_revision_is_linear_empty_and_additive() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert 'revision: str = "20260825_0033"' in text
    assert 'down_revision: str | Sequence[str] | None = "20260824_0032"' in text
    assert text.count("op.create_table(") == 2
    assert "INSERT" not in text and "UPDATE" not in text and "op.bulk_insert" not in text


def test_gate_binding_requires_runtime_and_closed_profile() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert '"handle_id", name="pk_manifest_handoff_supervisor_gate_bindings"' in text
    assert "manifest_handoff_supervisor_runtime_bindings.handle_id" in text
    assert "profile IN ('writer','recovery')" in text
    assert "uq_manifest_handoff_supervisor_gate_gated_observation" in text
    assert "uq_manifest_handoff_supervisor_gate_terminal_observation" in text
    assert "gated_observation_id<>terminal_observation_id" in text


def test_artifact_reservations_are_global_and_role_closed() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert '"artifact_id",\n            name="pk_manifest_handoff_supervisor_gate_artifact_reservations"' in text
    assert '"handle_id", "role"' in text
    assert "uq_manifest_handoff_supervisor_gate_artifact_role" in text
    for role in ("wrapper_ready", "release_consumed", "terminal_envelope"):
        assert f"'{role}'" in text
    assert "release_token" not in text


def test_foundation_has_no_path_payload_cascade_seed_or_mutation() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    for forbidden in ("path", "payload", "ondelete=", "INSERT", "UPDATE", "DELETE"):
        assert forbidden not in text
    drops = [line.strip() for line in text.splitlines() if "op.drop_table" in line]
    assert "artifact_reservations" in drops[0] and "gate_bindings" in drops[1]


def test_store_and_lookup_ports_are_minimal_and_read_only() -> None:
    classes = _classes(PORTS)
    assert _methods(classes["ManifestHandoffSupervisorGateBindingStore"]) == ["bind_gate"]
    assert _methods(classes["ManifestHandoffSupervisorGateBindingLookup"]) == [
        "resolve_gate", "resolve_gate_artifact"]


def test_migration_gates_are_synchronized_to_33() -> None:
    gate = (ROOT / "tests/test_persistence_migration_gate.py").read_text()
    bundle = (ROOT / "tools/operational_release_bundle.py").read_text()
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    assert 'expected_head() == "20260826_0042"' in gate
    assert "EXPECTED_MIGRATION_COUNT = 42" in bundle
    assert "**42 lineare Migrationen**, Head\n  `20260826_0042`" in roadmap


def test_roadmap_records_lq473_and_next_adapter() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    assert "- LQ-473 persistent immutable supervisor gate binding foundation:" in roadmap
    assert "lq-473-persistent-immutable-supervisor-gate-binding-foundation.md" in roadmap
    assert "nächster Slice LQ-474" in roadmap
