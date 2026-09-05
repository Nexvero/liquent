import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "src/liquent_platform/persistence/manifest_handoff_supervisor_cleanup_mutation_authority.py"


def _text() -> str:
    return ADAPTER.read_text(encoding="utf-8")


def _methods() -> set[str]:
    tree = ast.parse(_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == "DatabaseManifestHandoffSupervisorCleanupMutationAuthorities")
    return {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}


def test_sixteen_source_specific_public_methods_exist() -> None:
    methods = _methods()
    for source in ("management", "hold", "recovery", "reference"):
        assert f"permits_cleanup_{source}_mutation" in methods
        assert f"bootstrap_cleanup_{source}_mutation_authority" in methods
        assert f"change_cleanup_{source}_mutation_authority" in methods
        assert f"recover_cleanup_{source}_mutation_authority" in methods


def test_public_methods_hardcode_source_and_accept_no_kind() -> None:
    text = _text()
    for source in ("management", "hold", "recovery", "reference"):
        assert f'_SOURCES["{source}"]' in text
    for name in _methods():
        if not name.startswith("_"):
            node = next(node for node in ast.parse(text).body if isinstance(node, ast.ClassDef)
                        and node.name == "DatabaseManifestHandoffSupervisorCleanupMutationAuthorities")
            method = next(item for item in node.body if isinstance(item, ast.FunctionDef) and item.name == name)
            assert "kind" not in {arg.arg for arg in method.args.args}


def test_lookup_requires_active_current_member_user_and_scope() -> None:
    text = _text()
    section = text[text.index("def _permits"):text.index("def _bootstrap")]
    assert "_current current_set" in section
    assert "_members member" in section
    assert "member.status='active'" in section
    assert "users.status='active'" in section
    assert "scopes.status='active'" in section


def test_bootstrap_is_retry_first_empty_and_atomic() -> None:
    text = _text()
    section = text[text.index("def _bootstrap"):text.index("def _change")]
    assert section.index("bootstrap_id=:id") < section.index("SELECT 1 FROM {root}_sets")
    assert "_active_foundations" in section
    assert "_insert_set" in section
    assert "_bootstraps" in section
    assert "sequence" not in section or ", 1," in section


def test_lifecycle_retry_precedes_current_authority_checks() -> None:
    text = _text()
    section = text[text.index("def _change"):text.index("def _recover")]
    assert section.index("change_id=:id") < section.index("current = self._current")
    assert "existing.actor_user_id == values" in section
    assert "current.members.get(values" in section
    assert "_active_foundations" in section


def test_lifecycle_transition_matrix_and_effective_lockout_are_closed() -> None:
    text = _text()
    section = text[text.index("def _change"):text.index("def _recover")]
    assert '"grant" and previous is None' in section
    assert '"deactivate" and previous == "active"' in section
    assert '"reactivate" and previous == "inactive"' in section
    assert "_has_effective_member(connection, members" in section
    assert "current.sequence + 1" in section


def test_recovery_is_retry_first_current_closed_and_historical() -> None:
    text = _text()
    section = text[text.index("def _recover"):text.index("class _Current")]
    assert section.index("recovery_id=:id") < section.index("current = self._current")
    assert "current.revision_id != values" in section
    assert "values[\"target\"] not in current.members" in section
    assert "_effective_count" in section and "!= 0" in section
    assert 'members[values["target"]] = "active"' in section


def test_set_insert_writes_complete_members_before_pointer() -> None:
    text = _text()
    section = text[text.index("def _insert_set"):text.index("def _load_set")]
    assert section.index("_sets") < section.index("for user, status in members.items()")
    assert section.index("for user, status in members.items()") < section.index("UPDATE {root}_current")
    assert "INSERT INTO {root}_current" in section


def test_lifecycle_and_recovery_reject_regressing_clock() -> None:
    text = _text()
    assert text.count("if now < current.created_at:") == 2
    assert "sets.created_at" in text
    assert "_utc(row.created_at)" in text


def test_postgres_lock_sqlite_and_detail_free_boundary_exist() -> None:
    text = _text()
    assert "LOCK TABLE identity_users,manifest_handoff_registry_scopes" in text
    for suffix in ("_sets", "_members", "_current", "_bootstraps", "_changes", "_recoveries"):
        assert suffix in text[text.index("LOCK TABLE"):]
    assert 'connection.dialect.name != "sqlite"' in text
    assert "ManifestHandoffRegistryUnavailable" in text


def test_no_cleanup_revision_clearance_file_or_wiring_effect() -> None:
    text = _text()
    for forbidden in (
        "cleanup_management_revisions", "cleanup_hold_revisions",
        "cleanup_recovery_revisions", "cleanup_reference_revisions",
        "cleanup_clearances", "cleanup_attempts", "from pathlib", "open(",
        "unlink", "rmdir", "create_app", "WorkspaceId", "Permission",
    ):
        assert forbidden not in text


def test_roadmap_records_lq505_and_lq506() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-505 persistent cleanup mutation authority adapter:" in roadmap
    assert "lq-505-persistent-cleanup-mutation-authority-adapter.md" in roadmap
    assert "nächster Slice LQ-506" in roadmap
