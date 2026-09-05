from pathlib import Path


ROOT = Path(__file__).parents[1]
MIGRATION = ROOT / "src/liquent_platform/persistence/alembic/versions/20260826_0037_cleanup_revision_change_bindings.py"


def _text() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_revision_is_linear_after_0036() -> None:
    text = _text()
    assert 'revision: str = "20260826_0037"' in text
    assert 'down_revision: str | Sequence[str] | None = "20260825_0036"' in text


def test_four_empty_source_specific_change_tables_are_created() -> None:
    text = _text()
    assert text.count("op.create_table(") == 2
    assert '"manifest_handoff_supervisor_cleanup_management_changes"' in text
    for kind in ("hold", "recovery", "reference"):
        assert f'_target_change_table("{kind}")' in text
    for forbidden in ("INSERT ", "UPDATE ", "DELETE ", "op.bulk_insert"):
        assert forbidden not in text


def test_management_change_binds_result_and_expected_to_actor_scope() -> None:
    text = _text()
    assert '["revision_id", "actor_user_id", "scope_id"]' in text
    assert '["expected_revision_id", "actor_user_id", "scope_id"]' in text
    assert text.count("cleanup_management_revisions.revision_id") == 2


def test_target_changes_bind_result_and_expected_to_same_directory() -> None:
    text = _text()
    assert '["revision_id", "directory_id"]' in text
    assert '["expected_revision_id", "directory_id"]' in text
    assert 'revisions = f"manifest_handoff_supervisor_cleanup_{kind}_revisions"' in text


def test_change_and_result_identities_are_non_reusable() -> None:
    text = _text()
    assert 'sa.PrimaryKeyConstraint("change_id"' in text
    assert 'sa.UniqueConstraint("revision_id"' in text
    assert "length(change_id)>0" in text
    assert "expected_revision_id<>revision_id" in text


def test_clearance_does_not_get_a_redundant_change_table() -> None:
    text = _text()
    assert "cleanup_clearance_changes" not in text
    assert "cleanup_attempts" not in text
    assert "cleanup_clearances" not in text


def test_no_authority_role_allow_path_or_effect_is_added() -> None:
    text = _text()
    for forbidden in (
        "authority", "role", "permission", "allow", "root_path", "leaf",
        "filename", "open(", "unlink", "rmdir",
    ):
        assert forbidden not in text.lower()


def test_downgrade_removes_only_change_bindings_in_reverse_order() -> None:
    section = _text()[_text().index("def downgrade") :]
    order = ("reference_changes", "recovery_changes", "hold_changes", "management_changes")
    positions = [section.index(value) for value in order]
    assert positions == sorted(positions)
    assert "_revisions" not in section


def test_current_head_bundle_and_roadmap_are_synchronized() -> None:
    gate = (ROOT / "tests/test_persistence_migration_gate.py").read_text(encoding="utf-8")
    bundle = (ROOT / "tools/operational_release_bundle.py").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert 'expected_head() == "20260826_0042"' in gate
    assert "EXPECTED_MIGRATION_COUNT = 42" in bundle
    assert "**42 lineare Migrationen**, Head\n  `20260826_0042`" in roadmap


def test_roadmap_records_lq501_and_lq502() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-501 persistent cleanup revision change identity foundation:" in roadmap
    assert "lq-501-persistent-cleanup-revision-change-identity-foundation.md" in roadmap
    assert "nächster Slice LQ-502" in roadmap
