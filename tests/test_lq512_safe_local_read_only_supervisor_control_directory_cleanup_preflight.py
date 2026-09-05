import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "src/liquent_platform/transport/manifest_handoff_supervisor_control_directory_cleanup_preflight.py"
ARTIFACTS = ROOT / "src/liquent_platform/transport/manifest_handoff_supervisor_control_artifacts.py"


def _text() -> str:
    return ADAPTER.read_text(encoding="utf-8")


def test_adapter_implements_only_preflight_public_effect() -> None:
    tree = ast.parse(_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    methods = {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}
    assert "prepare_control_directory_cleanup" in methods
    assert not {"remove", "delete", "cleanup", "claim", "reconcile"} & methods


def test_request_resolves_started_attempt_and_current_clearance_internally() -> None:
    text = _text()
    assert "self._attempts(request.attempt_id)" in text
    assert "type(attempt) is not CleanupManifestHandoffSupervisorControlDirectory" in text
    assert "attempt.directory_id != request.directory_id" in text
    assert "clearance = self._clearances(attempt)" in text
    assert "type(clearance) is not ClearedManifestHandoffSupervisorControlDirectoryCleanup" in text
    assert "clearance.request != attempt" in text


def test_root_and_retired_leaf_are_descriptor_bound_no_follow() -> None:
    text = _text()
    assert "os.lstat(self._root)" in text
    assert "os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC" in text
    assert "name = clearance.retired.leaf.value" in text
    assert "os.open(name, _OPEN_DIRECTORY, dir_fd=root)" in text
    assert "stat.S_IMODE(facts.st_mode) == 0o700" in text
    assert "entry.st_dev == current.st_dev" in text
    assert "entry.st_ino == current.st_ino" in text


def test_missing_leaf_returns_bound_absent_after_revalidation() -> None:
    text = _text()
    section = text[text.index("except FileNotFoundError"):text.index("except OSError")]
    assert "self._same_root(root)" in section
    assert "current = self._clearances(attempt)" in section
    assert "current != clearance" in section
    assert "AbsentManifestHandoffSupervisorControlDirectoryCleanupPreflight(" in section


def test_inventory_uses_all_closed_roles_and_shared_canonical_names() -> None:
    text = _text()
    artifacts = ARTIFACTS.read_text(encoding="utf-8")
    assert "_ROLES = tuple(ManifestHandoffSupervisorControlArtifactRole)" in text
    assert "for role in _ROLES" in text
    assert "canonical_manifest_handoff_supervisor_control_artifact_name(role)" in text
    assert "def canonical_manifest_handoff_supervisor_control_artifact_name(role):" in artifacts
    assert artifacts.count("canonical_manifest_handoff_supervisor_control_artifact_name(") >= 3


def test_inventory_is_exact_before_and_after_artifact_reads() -> None:
    text = _text()
    assert text.count("self._names(leaf) != set(expected)") == 2
    assert "names = os.listdir(descriptor)" in text
    assert "for filename, record in expected.items()" in text
    assert "self._matches_artifact(leaf, filename, record)" in text


def test_files_are_private_single_link_bounded_and_race_checked() -> None:
    text = _text()
    assert "os.open(name, _OPEN_FILE, dir_fd=directory)" in text
    assert "stat.S_ISREG(facts.st_mode)" in text
    assert "stat.S_IMODE(facts.st_mode) == 0o600" in text
    assert "facts.st_nlink == 1" in text
    assert "remaining = _MAX_BYTES + 1" in text
    for field in ("st_dev", "st_ino", "st_mode", "st_uid", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns"):
        assert field in text


def test_canonical_bytes_match_complete_persistent_record() -> None:
    text = _text()
    assert "document = self._codec.decode_content(content)" in text
    assert "encoded = self._codec.encode(document)" in text
    for binding in (
        "document.artifact_id == record.artifact_id",
        "document.handle_id == record.handle_id",
        "document.role is record.role",
        "document.correlation_id == record.correlation_id",
        "encoded.facts == record.facts",
        "encoded.content.value == content",
    ):
        assert binding in text


def test_final_revalidation_precedes_internal_prepared_result() -> None:
    text = _text()
    section = text[text.index("current_clearance = self._clearances(attempt)"):
                   text.index("return PreparedManifestHandoffSupervisorControlDirectoryCleanup")]
    assert "current_artifacts = self._persistent_artifacts(clearance)" in section
    assert "current_clearance != clearance or current_artifacts != artifacts" in section
    assert "self._new_preflight_id()" in text
    assert "now < lower" in text


def test_adapter_has_no_mutation_persistence_authority_or_wiring_power() -> None:
    text = _text()
    for forbidden in (
        "os.O_WRONLY", "os.O_RDWR", "os.mkdir", "os.link", "os.rename",
        "os.replace", "os.unlink", "os.rmdir", "os.fsync", "chmod", "chown",
        "sqlalchemy", "INSERT ", "UPDATE ", "DELETE ", "SessionPrincipal",
        "WorkspaceId", "Permission", "create_app",
    ):
        assert forbidden not in text


def test_roadmap_records_lq512_and_lq513() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-512 safe local read-only supervisor control-directory cleanup preflight:" in roadmap
    assert "lq-512-safe-local-read-only-supervisor-control-directory-cleanup-preflight.md" in roadmap
    assert "nächster Slice LQ-513" in roadmap
