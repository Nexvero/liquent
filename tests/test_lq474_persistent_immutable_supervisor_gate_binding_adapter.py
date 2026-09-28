import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "src/liquent_platform/persistence/manifest_handoff_supervisor_gate_bindings.py"


def _text() -> str:
    return ADAPTER.read_text(encoding="utf-8")


def _methods() -> set[str]:
    tree = ast.parse(_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    return {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}


def test_adapter_implements_store_and_both_lookups() -> None:
    assert {"bind_gate", "resolve_gate", "resolve_gate_artifact"} <= _methods()


def test_binding_requires_matching_runtime_control_and_journal_profile() -> None:
    text = _text()
    assert "_PREREQUISITE" in text
    assert "prerequisite.control_directory_id != values[\"control\"]" in text
    assert "prerequisite.capability != values[\"profile\"]" in text
    assert "return None" in text


def test_exact_retry_reconstructs_every_role_before_comparison() -> None:
    text = _text()
    assert "reconstructed = self._binding(transaction, existing[0])" in text
    assert "reconstructed == binding" in text
    assert "ManifestHandoffSupervisorGateBindingConflict()" in text
    assert "if len(reservations) != 3" in text
    assert 'set(roles) != {"wrapper_ready", "release_consumed", "terminal_envelope"}' in text


def test_occupied_observations_and_artifacts_block_new_binding() -> None:
    text = _text()
    assert "_OCCUPIED_OBSERVATION" in text and "_OCCUPIED_ARTIFACT" in text
    assert "gated_observation_id=:gated OR terminal_observation_id=:terminal" in text
    assert "artifact_id IN (:ready,:consumed,:terminal_artifact)" in text


def test_binding_and_three_roles_are_inserted_in_one_write_action() -> None:
    text = _text()
    assert "INSERT INTO manifest_handoff_supervisor_gate_bindings" in text
    assert '(("wrapper_ready", "ready"),' in text
    assert '("release_consumed", "consumed")' in text
    assert '("terminal_envelope", "terminal_artifact")' in text
    assert "INSERT INTO manifest_handoff_supervisor_gate_artifact_reservations" in text
    assert "release_token" not in text


def test_lookup_joins_runtime_and_journal_and_revalidates_profile() -> None:
    text = _text()
    assert text.count("JOIN manifest_handoff_supervisor_runtime_bindings") >= 2
    assert text.count("JOIN manifest_handoff_supervisor_journal_jobs") >= 2
    assert "if row.profile != row.capability" in text
    assert "ManifestHandoffSupervisorControlDirectoryId(_decode(row.control_directory_id))" in text
    assert "_utc(row.bound_at)" in text


def test_postgres_lock_sqlite_and_detail_free_boundary_are_present() -> None:
    text = _text()
    for table in ("journal_jobs", "runtime_bindings", "gate_bindings", "gate_artifact_reservations"):
        assert table in text[text.index("_LOCK"):text.index("_BINDING_BY_HANDLE")]
    assert 'connection.dialect.name == "postgresql"' in text
    assert 'connection.dialect.name != "sqlite"' in text
    assert "ManifestHandoffRegistryUnavailable" in text


def test_no_file_engine_authority_mutation_or_wiring() -> None:
    text = _text()
    for forbidden in ("open(", "Path", "os.", "subprocess", "docker", "socket",
                      "SessionPrincipal", "Permission", "UPDATE ", "DELETE "):
        assert forbidden not in text


def test_roadmap_records_lq474_and_next_prepare_orchestration() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-474 persistent immutable supervisor gate binding adapter:" in roadmap
    assert "lq-474-persistent-immutable-supervisor-gate-binding-adapter.md" in roadmap
    assert "nächster Slice LQ-475" in roadmap
