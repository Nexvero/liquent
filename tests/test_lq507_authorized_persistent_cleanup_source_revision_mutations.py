import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "src/liquent_platform/persistence/manifest_handoff_supervisor_cleanup_revision_mutations.py"


def _text() -> str:
    return ADAPTER.read_text(encoding="utf-8")


def _methods() -> set[str]:
    tree = ast.parse(_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == "DatabaseManifestHandoffSupervisorCleanupRevisionMutations")
    return {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}


def test_four_source_specific_mutation_methods_exist() -> None:
    assert {
        "change_control_directory_cleanup_management",
        "change_control_directory_cleanup_hold",
        "change_control_directory_cleanup_recovery",
        "change_control_directory_cleanup_references",
    } <= _methods()


def test_public_target_methods_hardcode_source_without_caller_kind() -> None:
    text = _text()
    for source in ("hold", "recovery", "reference"):
        assert f'_SOURCES["{source}"]' in text
    tree = ast.parse(text)
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == "DatabaseManifestHandoffSupervisorCleanupRevisionMutations")
    for method in cls.body:
        if isinstance(method, ast.FunctionDef) and method.name.startswith("change_control_"):
            assert "kind" not in {arg.arg for arg in method.args.args}


def test_management_retry_joins_revision_change_and_authorization_first() -> None:
    text = _text()
    action = text[text.index("def _write_management"):text.index("def _write_target")]
    assert action.index("_management_retry") < action.index("_authority(")
    retry = text[text.index("def _management_retry"):text.index("def _target_retry")]
    assert "management_changes change" in retry
    assert "management_revisions revision" in retry
    assert "management_change_authorizations authorization" in retry
    assert "authorized_by_user_id == values" in retry


def test_management_checks_current_authority_target_foundations_and_expected_latest() -> None:
    text = _text()
    section = text[text.index("def _write_management"):text.index("def _write_target")]
    assert '_authority(connection, "management"' in section
    assert "_active_foundations" in section
    assert "_latest_management" in section
    assert "_expected(latest" in section
    assert "latest.sequence_number + 1" in section


def test_target_retry_precedes_target_and_authority_resolution() -> None:
    text = _text()
    section = text[text.index("def _write_target"):text.index("class _Authority")]
    assert section.index("_target_retry") < section.index("self._target(")
    assert section.index("self._target(") < section.index("self._authority(")
    retry = text[text.index("def _target_retry"):text.index("def _expected")]
    assert "source.changes" in retry and "source.revisions" in retry
    assert "source.authorizations" in retry
    assert "authorized_by_user_id == values" in retry


def test_target_scope_is_derived_from_retired_directory_and_terminal_journal() -> None:
    text = _text()
    section = text[text.index("def _target(self"):text.index("def _management_retry")]
    assert "manifest_handoff_supervisor_control_directories directory" in section
    assert "manifest_handoff_supervisor_journal_jobs job" in section
    assert "manifest_handoff_supervisor_journal_transitions transition" in section
    assert 'row.kind != "terminal_observed"' in section
    assert "RetiredManifestHandoffSupervisorControlDirectory" in section
    assert "row.scope_id" in section


def test_current_authority_requires_active_member_user_scope_and_current_pointer() -> None:
    text = _text()
    section = text[text.index("def _authority"):text.index("def _target(self")]
    assert "_current current_set" in section
    assert "_members member" in section
    assert "member.status='active'" in section
    assert "users.status='active'" in section
    assert "scopes.status='active'" in section


def test_new_write_atomically_inserts_revision_change_and_authorization() -> None:
    text = _text()
    for table in (
        "cleanup_management_revisions", "cleanup_management_changes",
        "source.revisions", "source.changes",
    ):
        assert table in text
    assert text.count("self._insert_authorization(") == 2
    assert "_change_authorizations" in text
    assert "self._engine.begin()" in text


def test_expected_revision_sequences_and_monotone_times_are_checked() -> None:
    text = _text()
    assert "if latest is None: return expected is None" in text
    assert "return latest.revision_id == expected" in text
    assert text.count("latest.sequence_number + 1") == 2
    assert "now < _utc(latest.resolved_at)" in text
    assert "max(retired.retired_at, terminal_at, authority.created_at" in text


def test_postgres_lock_sqlite_and_detail_free_error_boundary_exist() -> None:
    text = _text()
    assert "LOCK TABLE identity_users,manifest_handoff_registry_scopes" in text
    assert "manifest_handoff_supervisor_journal_transitions" in text[text.index("LOCK TABLE"):]
    assert "{authorizations} IN SHARE ROW EXCLUSIVE MODE" in text[text.index("LOCK TABLE"):]
    assert 'connection.dialect.name != "sqlite"' in text
    assert "ManifestHandoffRegistryUnavailable" in text


def test_no_clearance_attempt_file_authority_lifecycle_or_wiring_effect() -> None:
    text = _text()
    for forbidden in (
        "cleanup_clearances", "cleanup_attempts", "_authority_bootstraps",
        "_authority_changes", "_authority_recoveries", "from pathlib", "open(",
        "unlink", "rmdir", "create_app", "WorkspaceId", "Permission",
    ):
        assert forbidden not in text


def test_roadmap_records_lq507_and_lq508() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-507 authorized persistent cleanup source revision mutations:" in roadmap
    assert "lq-507-authorized-persistent-cleanup-source-revision-mutations.md" in roadmap
    assert "nächster Slice LQ-508" in roadmap
