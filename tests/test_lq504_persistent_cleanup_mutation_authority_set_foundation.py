from pathlib import Path


ROOT = Path(__file__).parents[1]
MIGRATION = ROOT / "src/liquent_platform/persistence/alembic/versions/20260826_0038_cleanup_mutation_authority_sets.py"


def _text() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_revision_is_linear_after_0037() -> None:
    text = _text()
    assert 'revision: str = "20260826_0038"' in text
    assert 'down_revision: str | Sequence[str] | None = "20260826_0037"' in text


def test_four_inventories_create_twenty_four_empty_tables() -> None:
    text = _text()
    assert text.count("op.create_table(") == 6
    for kind, prefix in (("management", "mhscma"), ("hold", "mhsch"),
                         ("recovery", "mhscr"), ("reference", "mhscf")):
        assert f'_authority_inventory("{kind}", "{prefix}")' in text
    for forbidden in ("INSERT ", "UPDATE ", "DELETE ", "op.bulk_insert"):
        assert forbidden not in text


def test_sets_are_scope_bound_positive_and_sequenced() -> None:
    text = _text()
    assert '"scope_id", "sequence_number"' in text
    assert "manifest_handoff_registry_scopes.scope_id" in text
    assert "length(revision_id)>0" in text
    assert "sequence_number>0" in text


def test_members_are_complete_shape_user_bound_and_closed() -> None:
    text = _text()
    assert '"revision_id", "user_id"' in text
    assert '"revision_id", "scope_id", "user_id"' in text
    assert "identity_users.user_id" in text
    assert "status IN ('active','inactive')" in text


def test_current_pointer_binds_revision_and_scope() -> None:
    text = _text()
    assert 'f"{root}_current"' in text
    assert 'sa.PrimaryKeyConstraint("scope_id"' in text
    assert 'sa.UniqueConstraint("revision_id"' in text
    assert '["revision_id", "scope_id"]' in text


def test_bootstrap_is_once_per_scope_and_binds_target_member() -> None:
    text = _text()
    assert 'f"{root}_bootstraps"' in text
    assert 'sa.UniqueConstraint("scope_id"' in text
    assert '["result_revision_id", "scope_id", "target_user_id"]' in text
    assert "length(bootstrap_id)>0" in text


def test_lifecycle_binds_expected_actor_result_target_and_closed_intent() -> None:
    text = _text()
    assert '["expected_revision_id", "scope_id", "actor_user_id"]' in text
    assert '["result_revision_id", "scope_id", "target_user_id"]' in text
    assert "intent IN ('grant','deactivate','reactivate')" in text
    assert "expected_revision_id<>result_revision_id" in text


def test_recovery_binds_historical_and_result_target_membership() -> None:
    text = _text()
    section = text[text.index('f"{root}_recoveries"'):text.index("def upgrade")]
    assert '["expected_revision_id", "scope_id", "target_user_id"]' in section
    assert '["result_revision_id", "scope_id", "target_user_id"]' in section
    assert "length(recovery_id)>0" in section


def test_no_role_allow_target_path_or_effect_is_added() -> None:
    text = _text().lower()
    for forbidden in ("role", "permission", "allow", "directory_id", "root_path",
                      "leaf", "filename", "open(", "unlink", "rmdir"):
        assert forbidden not in text


def test_downgrade_is_source_and_dependency_reverse() -> None:
    section = _text()[_text().index("def downgrade") :]
    assert '("reference", "recovery", "hold", "management")' in section
    order = ("_recoveries", "_changes", "_bootstraps", "_current", "_members", "_sets")
    positions = [section.index(value) for value in order]
    assert positions == sorted(positions)


def test_current_head_bundle_and_roadmap_are_synchronized() -> None:
    gate = (ROOT / "tests/test_persistence_migration_gate.py").read_text(encoding="utf-8")
    bundle = (ROOT / "tools/operational_release_bundle.py").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert 'expected_head() == "20260826_0042"' in gate
    assert "EXPECTED_MIGRATION_COUNT = 42" in bundle
    assert "**42 lineare Migrationen**, Head\n  `20260826_0042`" in roadmap


def test_roadmap_records_lq504_and_lq505() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-504 persistent cleanup mutation authority set foundation:" in roadmap
    assert "lq-504-persistent-cleanup-mutation-authority-set-foundation.md" in roadmap
    assert "nächster Slice LQ-505" in roadmap
