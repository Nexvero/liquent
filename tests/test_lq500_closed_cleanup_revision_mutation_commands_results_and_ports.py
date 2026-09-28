import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
DOMAIN = ROOT / "src/liquent_platform/identity/manifest_handoff_supervisor_control_directory_cleanup_clearance_mutation.py"
PORTS = ROOT / "src/liquent_platform/identity/ports.py"


def _domain() -> str:
    return DOMAIN.read_text(encoding="utf-8")


def test_four_non_interchangeable_repr_free_change_ids_exist() -> None:
    text = _domain()
    for kind in ("Management", "Hold", "Recovery", "Reference"):
        assert f"class ManifestHandoffSupervisorControlDirectoryCleanup{kind}ChangeId:" in text
    assert text.count("value: str = field(repr=False)") == 4


def test_four_closed_commands_have_typed_expected_revisions() -> None:
    text = _domain()
    for kind in ("Management", "Hold", "Recovery", "Reference"):
        assert f"class ChangeManifestHandoffSupervisorControlDirectoryCleanup{kind}:" in text
        assert f"Cleanup{kind}RevisionId | None" in text
    assert "CleanupManagementStatus" in text
    assert text.count("CleanupClearanceDisposition") >= 4


def test_commands_bind_internal_targets_without_actor_role_or_time() -> None:
    text = _domain()
    management = text[text.index("class ChangeManifestHandoffSupervisorControlDirectoryCleanupManagement"):text.index("class ChangeManifestHandoffSupervisorControlDirectoryCleanupHold")]
    assert "target_user_id: UserId" in management
    assert "scope_id: ManifestHandoffRegistryScopeId" in management
    for kind in ("Hold", "Recovery", "Reference"):
        section = text[text.index(f"class ChangeManifestHandoffSupervisorControlDirectoryCleanup{kind}"):]
        assert "directory_id: ManifestHandoffSupervisorControlDirectoryId" in section
    for forbidden in ("principal", "role", "allow", "decided_at", "resolved_at"):
        assert forbidden not in text


def test_four_committed_results_bind_change_to_full_fact() -> None:
    text = _domain()
    assert "authority: ManifestHandoffSupervisorControlDirectoryCleanupManagementAuthority" in text
    for kind in ("Hold", "Recovery", "Reference"):
        assert f"class CommittedManifestHandoffSupervisorControlDirectoryCleanup{kind}Change:" in text
        assert f"decision: ManifestHandoffSupervisorControlDirectoryCleanup{kind}Decision" in text
    assert "_validate_committed_target(" in text


def test_mutation_conflict_is_detail_free() -> None:
    tree = ast.parse(_domain())
    conflict = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                    and node.name.endswith("RevisionMutationConflict"))
    fields = [node for node in conflict.body if isinstance(node, ast.AnnAssign)]
    assert fields == []


def test_four_authorized_mutation_ports_keep_principal_separate() -> None:
    text = PORTS.read_text(encoding="utf-8")
    for kind, method in (
        ("Management", "change_control_directory_cleanup_management"),
        ("Hold", "change_control_directory_cleanup_hold"),
        ("Recovery", "change_control_directory_cleanup_recovery"),
        ("Reference", "change_control_directory_cleanup_references"),
    ):
        assert f"class AuthorizedManifestHandoffSupervisorControlDirectoryCleanup{kind}Mutation(Protocol):" in text
        section = text[text.index(f"class AuthorizedManifestHandoffSupervisorControlDirectoryCleanup{kind}Mutation"):]
        assert f"def {method}(" in section
        assert "principal: SessionPrincipal" in section
        assert f"command: ChangeManifestHandoffSupervisorControlDirectoryCleanup{kind}" in section


def test_clearance_creation_port_accepts_only_principal_and_closed_request() -> None:
    text = PORTS.read_text(encoding="utf-8")
    section = text[text.index("class AuthorizedManifestHandoffSupervisorControlDirectoryCleanupClearanceCreation"):]
    assert "principal: SessionPrincipal" in section
    assert "request: CleanupManifestHandoffSupervisorControlDirectory" in section
    assert "ClearedManifestHandoffSupervisorControlDirectoryCleanup" in section
    signature = section[:section.index("...")]
    for forbidden in ("clearance_id", "revision_id", "scope_id", "journal", "allow"):
        assert forbidden not in signature


def test_domain_has_no_schema_file_session_or_wiring_decision() -> None:
    text = _domain()
    for forbidden in (
        "sqlalchemy", "SessionPrincipal", "from pathlib", "open(", "unlink",
        "rmdir", "create_app", "WorkspaceId", "Permission",
    ):
        assert forbidden not in text


def test_roadmap_records_lq500_and_lq501() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-500 closed cleanup revision mutation commands results and ports:" in roadmap
    assert "lq-500-closed-cleanup-revision-mutation-commands-results-and-ports.md" in roadmap
    assert "nächster Slice LQ-501" in roadmap
