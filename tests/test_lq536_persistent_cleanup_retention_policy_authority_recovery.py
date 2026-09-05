from pathlib import Path


ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "src/liquent_platform/persistence/manifest_handoff_supervisor_cleanup_retention_policy.py"


def _text() -> str:
    return ADAPTER.read_text(encoding="utf-8")


def _section(start: str, end: str) -> str:
    text = _text()
    return text[text.index(f"    def {start}("):text.index(f"    def {end}(")]


def test_recovery_is_principal_free_and_requires_closed_command() -> None:
    section = _section("recover_cleanup_retention_policy_authority", "_current_authority")
    signature = section.split("\n", 1)[0]
    assert signature.endswith("(self, command):")
    assert "SessionPrincipal" not in signature
    assert "RecoverManifestHandoffSupervisorCleanupRetentionPolicyAuthority" in section
    assert '"target": _encode(command.target_user_id)' in section


def test_retry_precedes_current_lockout_generator_and_clock() -> None:
    section = _section("recover_cleanup_retention_policy_authority", "_current_authority")
    retry = section.index("WHERE recovery_id=:id")
    assert retry < section.index("self._current_authority")
    assert retry < section.index("active_users")
    assert retry < section.index("self._authority_revision()")
    assert retry < section.index("self._clock()")
    assert "row.target_user_id == values" in section
    assert "row.expected_revision_id == values" in section
    assert "self._load_authority(connection, row.result_revision_id)" in section


def test_expected_revision_is_exact_and_historical_target_required() -> None:
    section = _section("recover_cleanup_retention_policy_authority", "_current_authority")
    assert 'current[0] != values["expected"]' in section
    assert 'values["target"] not in members' in section
    assert "return None" in section


def test_target_must_be_currently_active_persistent_user() -> None:
    section = _section("recover_cleanup_retention_policy_authority", "_current_authority")
    assert "SELECT user_id FROM identity_users WHERE status='active'" in section
    assert 'values["target"] not in active_users' in section


def test_recovery_requires_complete_effective_lockout() -> None:
    section = _section("recover_cleanup_retention_policy_authority", "_current_authority")
    assert 'status == "active" and user in active_users' in section
    assert "for user, status in members.items()" in section
    lockout = section.index('if any(status == "active"')
    assert section.index("return None", lockout) < section.index("result_members = dict")


def test_result_copies_complete_set_and_activates_only_target() -> None:
    section = _section("recover_cleanup_retention_policy_authority", "_current_authority")
    assert "result_members = dict(members)" in section
    assert 'result_members[values["target"]] = "active"' in section
    assert "sequence + 1" in section
    assert "for user, status in sorted(result_members.items())" in section


def test_revision_is_internal_unique_and_time_monotone() -> None:
    section = _section("recover_cleanup_retention_policy_authority", "_current_authority")
    assert "self._authority_revision()" in section
    assert "result_id == revision_id" in section
    assert "SELECT 1 FROM {_SETS} WHERE revision_id=:revision" in section
    assert "if now < created_at" in section


def test_members_pointer_and_recovery_fact_are_atomic_and_ordered() -> None:
    section = _section("recover_cleanup_retention_policy_authority", "_current_authority")
    member_insert = section.index("for user, status in sorted")
    pointer = section.index("UPDATE {_CURRENT}")
    recovery = section.index("INSERT INTO {_RECOVERIES}")
    assert section.index("INSERT INTO {_SETS}") < member_insert < pointer < recovery
    assert "WHERE data_class=:class AND revision_id=:expected" in section
    assert "updated.rowcount != 1" in section
    assert "return self._access(action, True)" in section


def test_postgres_lock_includes_recovery_table() -> None:
    lock = _text()[_text().index("LOCK TABLE identity_users,"):]
    assert "{_RECOVERIES}" in lock
    assert "IN SHARE ROW EXCLUSIVE MODE" in lock


def test_no_operator_migration_file_or_wiring_effect() -> None:
    text = _text()
    for forbidden in ("argparse", "alembic", "from pathlib", "open(", "unlink", "create_app"):
        assert forbidden not in text


def test_roadmap_records_lq536_and_lq537() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-536 persistent supervisor cleanup retention policy authority recovery:" in roadmap
    assert "lq-536-persistent-supervisor-cleanup-retention-policy-authority-recovery.md" in roadmap
    assert "nächster Slice LQ-537" in roadmap
