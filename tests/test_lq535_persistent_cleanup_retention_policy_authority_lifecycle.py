from pathlib import Path


ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "src/liquent_platform/persistence/manifest_handoff_supervisor_cleanup_retention_policy.py"


def _text() -> str:
    return ADAPTER.read_text(encoding="utf-8")


def _section(start: str, end: str) -> str:
    text = _text()
    return text[text.index(f"    def {start}("):text.index(f"    def {end}(")]


def test_lifecycle_requires_exact_principal_and_closed_command() -> None:
    section = _section("change_cleanup_retention_policy_authority", "_current_authority")
    assert "type(principal) is not SessionPrincipal" in section
    assert "ChangeManifestHandoffSupervisorCleanupRetentionPolicyAuthority" in section
    assert '"actor": _encode(principal.user_id)' in section
    assert '"target": _encode(command.target_user_id)' in section


def test_retry_is_first_and_binds_all_original_inputs() -> None:
    section = _section("change_cleanup_retention_policy_authority", "_current_authority")
    retry = section.index("WHERE change_id=:id")
    assert retry < section.index("self._current_authority")
    assert retry < section.index("self._authority_revision()")
    assert retry < section.index("self._clock()")
    for field in ("actor_user_id", "target_user_id", "expected_revision_id", "intent"):
        assert f"row.{field}" in section
    assert "self._load_authority(connection, row.result_revision_id)" in section


def test_current_revision_actor_and_target_are_system_of_record_bound() -> None:
    section = _section("change_cleanup_retention_policy_authority", "_current_authority")
    assert 'current[0] != values["expected"]' in section
    assert 'members.get(values["actor"]) != "active"' in section
    assert "SELECT user_id FROM identity_users WHERE status='active'" in section
    assert 'values["actor"] not in active_users' in section
    assert 'values["target"] not in active_users' in section


def test_transition_matrix_is_closed() -> None:
    section = _section("change_cleanup_retention_policy_authority", "_current_authority")
    assert '"grant" and previous is None' in section
    assert '"deactivate" and previous == "active"' in section
    assert '"reactivate" and previous == "inactive"' in section
    assert '"inactive" if values["intent"] == "deactivate" else "active"' in section


def test_effective_lockout_is_rejected_before_revision_and_clock() -> None:
    section = _section("change_cleanup_retention_policy_authority", "_current_authority")
    lockout = section.index('status == "active" and user in active_users')
    assert lockout < section.index("self._authority_revision()")
    assert lockout < section.index("self._clock()")
    assert "ManifestHandoffSupervisorCleanupRetentionPolicyConflict()" in section[lockout:]


def test_revision_is_internal_unique_and_monotone() -> None:
    section = _section("change_cleanup_retention_policy_authority", "_current_authority")
    assert "self._authority_revision()" in section
    assert "result_id == revision_id" in section
    assert "SELECT 1 FROM {_SETS} WHERE revision_id=:revision" in section
    assert "sequence + 1" in section
    assert "if now < created_at" in section


def test_complete_members_are_inserted_before_expected_pointer_switch() -> None:
    section = _section("change_cleanup_retention_policy_authority", "_current_authority")
    member_insert = section.index("for user, status in sorted")
    assert section.index("INSERT INTO {_SETS}") < member_insert
    assert member_insert < section.index("UPDATE {_CURRENT}")
    assert "WHERE data_class=:class AND revision_id=:expected" in section
    assert "updated.rowcount != 1" in section
    assert section.index("UPDATE {_CURRENT}") < section.index("INSERT INTO {_AUTHORITY_CHANGES}")


def test_current_loader_rejects_missing_members_and_bad_status() -> None:
    current = _section("_current_authority", "_member_rows")
    members = _section("_member_rows", "_permits")
    assert "return None" in current
    assert "sequence_number < 1" in current
    assert "if not rows:" in members
    assert 'status not in ("active", "inactive")' in members


def test_postgres_lock_includes_authority_change_table() -> None:
    lock = _text()[_text().index("LOCK TABLE identity_users,"):]
    assert "{_AUTHORITY_CHANGES}" in lock
    assert "IN SHARE ROW EXCLUSIVE MODE" in lock


def test_no_operator_migration_or_wiring_effect() -> None:
    text = _text()
    for forbidden in ("create_app", "argparse", "alembic"):
        assert forbidden not in text


def test_roadmap_records_lq535_and_lq536() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-535 persistent supervisor cleanup retention policy authority lifecycle:" in roadmap
    assert "lq-535-persistent-supervisor-cleanup-retention-policy-authority-lifecycle.md" in roadmap
    assert "nächster Slice LQ-536" in roadmap
