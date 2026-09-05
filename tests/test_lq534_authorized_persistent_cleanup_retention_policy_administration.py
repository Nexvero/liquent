from pathlib import Path


ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "src/liquent_platform/persistence/manifest_handoff_supervisor_cleanup_retention_policy.py"


def _text() -> str:
    return ADAPTER.read_text(encoding="utf-8")


def _section(start: str, end: str) -> str:
    text = _text()
    return text[text.index(f"    def {start}("):text.index(f"    def {end}(")]


def test_change_method_requires_exact_principal_and_command() -> None:
    section = _section("change_cleanup_retention_policy", "_permits")
    assert "type(principal) is not SessionPrincipal" in section
    assert "type(command) is not ChangeManifestHandoffSupervisorCleanupRetentionPolicy" in section
    assert '"actor": _encode(principal.user_id)' in section


def test_retry_precedes_authority_expectation_clock_and_generator() -> None:
    section = _section("change_cleanup_retention_policy", "_permits")
    retry = section.index("WHERE change_id=:id")
    assert retry < section.index("self._permits")
    assert retry < section.index("current = connection.execute")
    assert retry < section.index("self._policy_revision()")
    assert retry < section.index("self._clock()")
    assert "row.actor_user_id == values" in section
    assert "ManifestHandoffSupervisorCleanupRetentionPolicyConflict()" in section


def test_authority_is_resolved_inside_same_write_action() -> None:
    section = _section("change_cleanup_retention_policy", "_permits")
    assert 'if not self._permits(connection, values["actor"]):' in section
    permit = _section("_permits", "_load_changed_policy")
    assert "FROM {_CURRENT}" in permit and "JOIN {_MEMBERS}" in permit
    assert "member.status='active'" in permit and "users.status='active'" in permit


def test_expected_revision_is_exact_and_never_wildcard() -> None:
    section = _section("change_cleanup_retention_policy", "_permits")
    assert "current_id = None if not current else current[0].revision_id" in section
    assert 'if current_id != values["expected"]:' in section
    assert "return ManifestHandoffSupervisorCleanupRetentionPolicyConflict()" in section


def test_deactivate_removes_pointer_and_writes_null_result() -> None:
    section = _section("change_cleanup_retention_policy", "_permits")
    assert 'values["intent"] == "deactivate"' in section
    assert "current_id is None" in section
    assert "DELETE FROM {_ACTIVE}" in section
    assert "VALUES (:id,:actor,:class,:expected,NULL,:intent,NULL,:now)" in section
    assert "ChangedManifestHandoffSupervisorCleanupRetentionPolicy(command, None)" in section


def test_replace_forbids_shortening_before_generator_and_clock() -> None:
    section = _section("change_cleanup_retention_policy", "_permits")
    maximum = section.index("SELECT MAX(minimum_retention_seconds)")
    rejection = section.index('values["seconds"] < maximum')
    assert maximum < rejection < section.index("self._policy_revision()")
    assert rejection < section.index("self._clock()", rejection)


def test_replace_rejects_revision_collision_and_atomically_updates_projection() -> None:
    section = _section("change_cleanup_retention_policy", "_permits")
    assert "SELECT 1 FROM {_POLICIES} WHERE revision_id=:revision" in section
    assert "INSERT INTO {_POLICIES}" in section
    assert "UPDATE {_ACTIVE} SET revision_id=:revision" in section
    assert "INSERT INTO {_ACTIVE}" in section
    assert "INSERT INTO {_CHANGES}" in section
    assert "return self._access(action, True)" in section


def test_historical_retry_does_not_depend_on_current_projection() -> None:
    section = _section("_load_changed_policy", "_load_bootstrap")
    assert "change.changed_at" in section
    assert "JOIN {_ACTIVE}" not in section


def test_postgres_write_lock_includes_change_table() -> None:
    text = _text()
    lock = text[text.index("LOCK TABLE identity_users,"):]
    assert "{_CHANGES}" in lock
    assert "IN SHARE ROW EXCLUSIVE MODE" in lock


def test_no_wiring_effect() -> None:
    text = _text()
    for forbidden in ("create_app", "argparse"):
        assert forbidden not in text


def test_roadmap_records_lq534_and_lq535() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-534 authorized persistent supervisor cleanup retention policy administration:" in roadmap
    assert "lq-534-authorized-persistent-supervisor-cleanup-retention-policy-administration.md" in roadmap
    assert "nächster Slice LQ-535" in roadmap
