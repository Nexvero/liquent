import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "src/liquent_platform/persistence/manifest_handoff_supervisor_cleanup_retention_policy.py"


def _text() -> str:
    return ADAPTER.read_text(encoding="utf-8")


def _method(name: str) -> str:
    text = _text()
    start = text.index(f"    def {name}(")
    positions = [position for token in ("\n    def ", "\n    @staticmethod")
                 if (position := text.find(token, start + 5)) >= 0]
    return text[start:min(positions) if positions else len(text)]


def test_adapter_retains_bootstrap_and_current_lookup_effects() -> None:
    tree = ast.parse(_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == "DatabaseManifestHandoffSupervisorCleanupRetentionPolicy")
    methods = {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}
    assert {"resolve_active_cleanup_retention_policy",
            "permits_cleanup_retention_policy_mutation",
            "bootstrap_cleanup_retention_policy"} <= methods


def test_constructor_requires_external_clock_and_separate_generators() -> None:
    section = _method("__init__")
    assert "clock:" in section
    assert "policy_revision_generator:" in section
    assert "authority_revision_generator:" in section
    assert "self._clock = clock" in section
    assert "datetime.now" not in section and "secrets" not in _text()


def test_bootstrap_is_retry_first_empty_foundation_and_active_user_only() -> None:
    section = _method("bootstrap_cleanup_retention_policy")
    assert section.index("WHERE bootstrap_id=:id") < section.index("SELECT EXISTS")
    assert "identity_users WHERE user_id=:target AND status='active'" in section
    assert "if inventory:" in section and "return None" in section
    assert "ManifestHandoffSupervisorCleanupRetentionPolicyConflict()" in section


def test_bootstrap_writes_both_histories_pointers_and_fact_atomically() -> None:
    section = _method("bootstrap_cleanup_retention_policy")
    for table in ("_POLICIES", "_SETS", "_MEMBERS", "_ACTIVE", "_CURRENT", "_BOOTSTRAPS"):
        assert f"INSERT INTO {{{table}}}" in section
    assert "self._engine.begin() if write" in _text()
    assert "policy_id == authority_id" in section


def test_policy_lookup_is_fresh_joined_neutral_and_revalidated() -> None:
    section = _method("resolve_active_cleanup_retention_policy")
    assert "JOIN {_POLICIES}" in section
    assert "if not rows:" in section and "return None" in section
    policy = _method("_policy")
    assert "seconds <= 0" in policy
    assert "ManifestHandoffSupervisorCleanupRetentionPolicyRevision(" in policy
    assert "ActiveManifestHandoffSupervisorCleanupRetentionPolicy(" in policy


def test_bootstrap_retry_reconstructs_history_not_current_projection() -> None:
    section = _method("_load_bootstrap")
    assert "bootstrapped_at" in section
    assert "JOIN {_ACTIVE}" not in section
    assert "bootstrap.policy_revision_id" in section


def test_permit_binds_principal_current_member_and_active_user() -> None:
    section = _method("permits_cleanup_retention_policy_mutation")
    assert "type(principal) is not SessionPrincipal" in section
    assert "self._permits(connection, actor)" in section
    helper = _method("_permits")
    assert "JOIN {_MEMBERS}" in helper
    assert "member.user_id=:actor" in helper
    assert "member.status='active'" in helper
    assert "users.status='active'" in helper
    assert "return bool(rows)" in helper


def test_postgres_lock_order_and_detail_free_boundary_exist() -> None:
    text = _text()
    assert "LOCK TABLE identity_users," in text
    for table in ("_POLICIES", "_ACTIVE", "_SETS", "_MEMBERS", "_CURRENT", "_BOOTSTRAPS"):
        assert table in text[text.index("LOCK TABLE identity_users,"):]
    assert 'connection.dialect.name not in ("postgresql", "sqlite")' in text
    assert "ManifestHandoffRegistryUnavailable" in text


def test_no_file_operator_or_wiring_effect() -> None:
    text = _text()
    for forbidden in ("from pathlib", "open(", "unlink", "argparse", "create_app"):
        assert forbidden not in text


def test_roadmap_records_lq533_and_lq534() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-533 persistent supervisor cleanup retention policy bootstrap and current lookups:" in roadmap
    assert "lq-533-persistent-supervisor-cleanup-retention-policy-bootstrap-and-current-lookups.md" in roadmap
    assert "nächster Slice LQ-534" in roadmap
