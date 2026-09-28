import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
DOMAIN = ROOT / "src/liquent_platform/identity/manifest_handoff_supervisor_cleanup_retention_policy.py"
PORTS = ROOT / "src/liquent_platform/identity/ports.py"


def _text() -> str:
    return DOMAIN.read_text(encoding="utf-8")


def test_five_operation_ids_are_separate_repr_free_values() -> None:
    text = _text()
    for name in (
        "PolicyBootstrapId", "PolicyChangeId", "PolicyAuthoritySetRevisionId",
        "PolicyAuthorityChangeId", "PolicyAuthorityRecoveryId",
    ):
        assert f"class ManifestHandoffSupervisorCleanupRetention{name}:" in text
    assert text.count("value: str = field(repr=False)") == 5


def test_policy_revision_is_closed_positive_second_resolution_and_utc() -> None:
    text = _text()
    section = text[text.index("class ManifestHandoffSupervisorCleanupRetentionPolicyRevision"):
                   text.index("class ActiveManifestHandoffSupervisorCleanupRetentionPolicy")]
    assert "SUPERVISOR_CONTROL_DIRECTORY" in section
    assert "minimum_retention: timedelta" in section
    assert "created_at: datetime" in section
    duration = ast.unparse(next(node for node in ast.parse(text).body
                                if isinstance(node, ast.FunctionDef)
                                and node.name == "_require_duration"))
    assert "value <= timedelta(0)" in duration
    assert "value.microseconds != 0" in duration


def test_active_projection_is_monotone_and_not_boolean_status() -> None:
    text = _text()
    section = text[text.index("class ActiveManifestHandoffSupervisorCleanupRetentionPolicy"):
                   text.index("class ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityStatus")]
    assert "policy:" in section and "activated_at: datetime" in section
    assert "self.activated_at < self.policy.created_at" in section
    assert "active: bool" not in section


def test_authority_set_is_complete_unique_and_has_active_member() -> None:
    text = _text()
    assert 'ACTIVE = "active"' in text and 'INACTIVE = "inactive"' in text
    assert 'GRANT = "grant"' in text
    assert 'DEACTIVATE = "deactivate"' in text
    assert 'REACTIVATE = "reactivate"' in text
    section = text[text.index("class ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySet"):
                   text.index("class BootstrapManifestHandoffSupervisorCleanupRetentionPolicy")]
    assert "type(self.members) is frozenset and bool(self.members)" in section
    assert "len({member.user_id for member in self.members}) == len(self.members)" in section
    assert "AuthorityStatus.ACTIVE" in section


def test_bootstrap_binds_target_and_duration_without_actor_or_revision() -> None:
    text = _text()
    section = text[text.index("class BootstrapManifestHandoffSupervisorCleanupRetentionPolicy"):
                   text.index("class BootstrappedManifestHandoffSupervisorCleanupRetentionPolicy")]
    assert "bootstrap_id:" in section
    assert "target_user_id: UserId" in section
    assert "minimum_retention: timedelta" in section
    for forbidden in ("SessionPrincipal", "revision_id", "disposition"):
        assert forbidden not in section


def test_policy_change_replace_and_deactivate_matrix_is_closed() -> None:
    text = _text()
    assert 'REPLACE = "replace"' in text
    section = text[text.index("class ChangeManifestHandoffSupervisorCleanupRetentionPolicy"):
                   text.index("class ChangedManifestHandoffSupervisorCleanupRetentionPolicy")]
    assert "expected_revision_id:" in section
    assert "minimum_retention: timedelta | None" in section
    assert "_require_duration(" in section
    assert "elif self.minimum_retention is not None" in section
    result = text[text.index("class ChangedManifestHandoffSupervisorCleanupRetentionPolicy"):
                  text.index("class ChangeManifestHandoffSupervisorCleanupRetentionPolicyAuthority")]
    assert "self.active_policy.policy.minimum_retention" in result
    assert "!= self.command.minimum_retention" in result
    assert "elif self.active_policy is not None" in result


def test_bootstrap_result_rebinds_duration_and_active_target() -> None:
    text = _text()
    section = text[text.index("class BootstrappedManifestHandoffSupervisorCleanupRetentionPolicy"):
                   text.index("class ManifestHandoffSupervisorCleanupRetentionPolicyChangeIntent")]
    assert "self.active_policy.policy.minimum_retention" in section
    assert "== self.command.minimum_retention" in section
    assert "member.user_id == self.command.target_user_id" in section
    assert "AuthorityStatus.ACTIVE" in section


def test_authority_lifecycle_and_recovery_commands_are_separate() -> None:
    text = _text()
    lifecycle = text[text.index("class ChangeManifestHandoffSupervisorCleanupRetentionPolicyAuthority"):
                     text.index("class RecoverManifestHandoffSupervisorCleanupRetentionPolicyAuthority")]
    recovery = text[text.index("class RecoverManifestHandoffSupervisorCleanupRetentionPolicyAuthority"):
                    text.index("class ManifestHandoffSupervisorCleanupRetentionPolicyConflict")]
    assert "intent:" in lifecycle and "change_id:" in lifecycle
    assert "recovery_id:" in recovery and "intent:" not in recovery
    assert "SessionPrincipal" not in lifecycle + recovery


def test_conflict_is_fieldless_and_module_has_no_runtime_power() -> None:
    text = _text()
    tree = ast.parse(text)
    conflict = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                    and node.name == "ManifestHandoffSupervisorCleanupRetentionPolicyConflict")
    assert not [node for node in conflict.body if isinstance(node, ast.AnnAssign)]
    for forbidden in ("sqlalchemy", "from pathlib", "import os", "argparse"):
        assert forbidden not in text


def test_ports_are_exact_lookup_policy_and_authority_surfaces() -> None:
    text = PORTS.read_text(encoding="utf-8")
    for cls, methods in (
        ("ManifestHandoffSupervisorCleanupRetentionPolicyLookup", ("resolve_active_cleanup_retention_policy",)),
        ("ManifestHandoffSupervisorCleanupRetentionPolicyAdministration", ("bootstrap_cleanup_retention_policy", "change_cleanup_retention_policy")),
        ("ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityAdministration", ("permits_cleanup_retention_policy_mutation", "change_cleanup_retention_policy_authority", "recover_cleanup_retention_policy_authority")),
    ):
        assert f"class {cls}(Protocol):" in text
        section = text[text.index(f"class {cls}(Protocol):"):]
        for method in methods:
            assert f"def {method}(" in section


def test_roadmap_records_lq531_and_lq532() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-531 closed supervisor cleanup retention policy and authority values and ports:" in roadmap
    assert "lq-531-closed-supervisor-cleanup-retention-policy-and-authority-values-and-ports.md" in roadmap
    assert "nächster Slice LQ-532" in roadmap
