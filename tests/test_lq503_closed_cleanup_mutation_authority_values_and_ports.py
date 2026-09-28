import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
DOMAIN = ROOT / "src/liquent_platform/identity/manifest_handoff_supervisor_cleanup_mutation_authority.py"
PORTS = ROOT / "src/liquent_platform/identity/ports.py"


def _domain() -> str:
    return DOMAIN.read_text(encoding="utf-8")


def test_sixteen_non_interchangeable_repr_free_ids_exist() -> None:
    text = _domain()
    for source in ("Management", "Hold", "Recovery", "Reference"):
        for suffix in ("SetRevisionId", "LifecycleChangeId", "BootstrapId", "RecoveryId"):
            assert f"class Cleanup{source}MutationAuthority{suffix}:" in text
    assert text.count("value: str = field(repr=False)") == 16


def test_status_intent_and_member_are_closed() -> None:
    text = _domain()
    for value in ('ACTIVE = "active"', 'INACTIVE = "inactive"', 'GRANT = "grant"',
                  'DEACTIVATE = "deactivate"', 'REACTIVATE = "reactivate"'):
        assert value in text
    assert "class ManifestHandoffSupervisorCleanupMutationAuthorityMember:" in text


def test_four_complete_set_types_bind_typed_revision_scope_and_members() -> None:
    text = _domain()
    for source in ("Management", "Hold", "Recovery", "Reference"):
        section = text[text.index(f"class Cleanup{source}MutationAuthoritySet:"):]
        assert f"revision_id: Cleanup{source}MutationAuthoritySetRevisionId" in section
        assert "scope_id: ManifestHandoffRegistryScopeId" in section
        assert "members: frozenset[ManifestHandoffSupervisorCleanupMutationAuthorityMember]" in section
    assert "len({member.user_id for member in value.members}) == len(value.members)" in text
    assert "any(member.status is ManifestHandoffSupervisorCleanupMutationAuthorityStatus.ACTIVE" in text


def test_four_lifecycle_commands_bind_expected_typed_revision() -> None:
    text = _domain()
    for source in ("Management", "Hold", "Recovery", "Reference"):
        assert f"class ChangeCleanup{source}MutationAuthority:" in text
        assert f"expected_revision_id: Cleanup{source}MutationAuthoritySetRevisionId" in text
    assert "_validate_lifecycle(" in text


def test_four_bootstrap_and_four_recovery_commands_are_separate() -> None:
    text = _domain()
    for source in ("Management", "Hold", "Recovery", "Reference"):
        assert f"class BootstrapCleanup{source}MutationAuthority:" in text
        assert f"class RecoverCleanup{source}MutationAuthority:" in text
        assert f"recovery_id: Cleanup{source}MutationAuthorityRecoveryId" in text
    assert "_validate_bootstrap(" in text and "_validate_recovery(" in text


def test_authority_conflict_is_fieldless() -> None:
    tree = ast.parse(_domain())
    conflict = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                    and node.name == "ManifestHandoffSupervisorCleanupMutationAuthorityConflict")
    assert not any(isinstance(node, ast.AnnAssign) for node in conflict.body)


def test_four_lookup_ports_return_server_side_bool() -> None:
    text = PORTS.read_text(encoding="utf-8")
    for source in ("Management", "Hold", "Recovery", "Reference"):
        assert f"class Cleanup{source}MutationAuthorityLookup(Protocol):" in text
        section = text[text.index(f"class Cleanup{source}MutationAuthorityLookup"):]
        assert "principal: SessionPrincipal, scope_id: ManifestHandoffRegistryScopeId" in section
        assert ") -> bool: ..." in section


def test_twelve_mutation_ports_remain_source_and_boundary_specific() -> None:
    text = PORTS.read_text(encoding="utf-8")
    for source in ("Management", "Hold", "Recovery", "Reference"):
        assert f"class Cleanup{source}MutationAuthorityBootstrap(Protocol):" in text
        assert f"class Cleanup{source}MutationAuthorityLifecycle(Protocol):" in text
        assert f"class OfflineCleanup{source}MutationAuthorityRecovery(Protocol):" in text
        lifecycle = text[text.index(f"class Cleanup{source}MutationAuthorityLifecycle"):]
        assert "principal: SessionPrincipal" in lifecycle
        recovery = text[text.index(f"class OfflineCleanup{source}MutationAuthorityRecovery"):]
        assert "principal: SessionPrincipal" not in recovery[:recovery.index("...")]


def test_no_schema_file_generic_kind_or_wiring_decision() -> None:
    text = _domain()
    for forbidden in (
        "sqlalchemy", "AuthorityKind", "from pathlib", "open(", "unlink", "rmdir",
        "create_app", "WorkspaceId", "Permission", "SessionPrincipal",
    ):
        assert forbidden not in text


def test_roadmap_records_lq503_and_lq504() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-503 closed cleanup mutation authority values and ports:" in roadmap
    assert "lq-503-closed-cleanup-mutation-authority-values-and-ports.md" in roadmap
    assert "nächster Slice LQ-504" in roadmap
