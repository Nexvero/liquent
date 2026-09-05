from pathlib import Path


ROOT = Path(__file__).parents[1]
MIGRATION = ROOT / "src/liquent_platform/persistence/alembic/versions/20260826_0039_cleanup_revision_change_authorizations.py"


def _text() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_revision_is_linear_after_0038() -> None:
    text = _text()
    assert 'revision: str = "20260826_0039"' in text
    assert 'down_revision: str | Sequence[str] | None = "20260826_0038"' in text


def test_four_empty_source_specific_authorization_tables_are_created() -> None:
    text = _text()
    assert text.count("_authorization_table(") == 5
    for kind in ("management", "hold", "recovery", "reference"):
        assert f'"{kind}"' in text
        assert f"mh_supervisor_cleanup_{kind}_change_authorizations" in text
    for forbidden in ("INSERT ", "UPDATE ", "DELETE ", "op.bulk_insert"):
        assert forbidden not in text


def test_change_id_is_primary_key_and_source_change_foreign_key() -> None:
    text = _text()
    assert 'sa.PrimaryKeyConstraint("change_id"' in text
    assert '["change_id"], [f"{change_table}.change_id"]' in text
    for kind in ("management", "hold", "recovery", "reference"):
        assert f"manifest_handoff_supervisor_cleanup_{kind}_changes" in text


def test_authorizer_is_bound_to_source_set_revision_and_scope_member() -> None:
    text = _text()
    assert '["authority_set_revision_id", "scope_id", "authorized_by_user_id"]' in text
    assert 'f"{authority}_members.revision_id"' in text
    assert 'f"{authority}_members.scope_id"' in text
    assert 'f"{authority}_members.user_id"' in text


def test_authorization_time_is_required_without_caller_decision_fields() -> None:
    text = _text().lower()
    assert 'sa.column("authorized_at", sa.datetime(timezone=true), nullable=false)' in text
    for forbidden in ("allow", "role", "permission", "evidence", "session_id", "csrf"):
        assert forbidden not in text


def test_no_target_directory_path_or_cleanup_effect_is_added() -> None:
    text = _text().lower()
    for forbidden in ("directory_id", "handle_id", "root_path", "leaf", "filename",
                      "cleanup_clearance", "cleanup_attempt", "open(", "unlink", "rmdir"):
        assert forbidden not in text


def test_downgrade_removes_only_authorizations_in_reverse_source_order() -> None:
    section = _text()[_text().index("def downgrade") :]
    order = ("reference_change", "recovery_change", "hold_change", "management_change")
    positions = [section.index(value) for value in order]
    assert positions == sorted(positions)
    assert "manifest_handoff_supervisor_cleanup_management_changes" not in section


def test_current_head_bundle_and_roadmap_are_synchronized() -> None:
    gate = (ROOT / "tests/test_persistence_migration_gate.py").read_text(encoding="utf-8")
    bundle = (ROOT / "tools/operational_release_bundle.py").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert 'expected_head() == "20260826_0042"' in gate
    assert "EXPECTED_MIGRATION_COUNT = 42" in bundle
    assert "**42 lineare Migrationen**, Head\n  `20260826_0042`" in roadmap


def test_roadmap_records_lq506_and_lq507() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-506 persistent cleanup revision change authorization binding foundation:" in roadmap
    assert "lq-506-persistent-cleanup-revision-change-authorization-binding-foundation.md" in roadmap
    assert "nächster Slice LQ-507" in roadmap
