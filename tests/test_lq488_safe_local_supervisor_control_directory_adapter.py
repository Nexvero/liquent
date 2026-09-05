import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "src/liquent_platform/transport/manifest_handoff_supervisor_control_directories.py"


def _text() -> str:
    return ADAPTER.read_text(encoding="utf-8")


def _methods() -> set[str]:
    tree = ast.parse(_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    return {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}


def test_adapter_has_only_create_and_active_resolution_public_effects() -> None:
    methods = _methods()
    assert {"create_reserved", "resolve_active"} <= methods
    assert not {"remove", "delete", "retire", "rotate", "rename", "prune"} & methods


def test_root_is_absolute_injected_and_never_created() -> None:
    text = _text()
    assert "not root.is_absolute()" in text
    constructor = text[text.index("def __init__"):text.index("def __repr__")]
    assert not any(value in constructor for value in ("os.open", "os.mkdir", "exists("))


def test_root_is_opened_no_follow_and_revalidated_each_time() -> None:
    text = _text()
    assert "os.lstat(self._root)" in text
    assert "os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC" in text
    assert "path_facts.st_dev != descriptor_facts.st_dev" in text
    assert "path_facts.st_ino != descriptor_facts.st_ino" in text
    assert text.count("self._same_root(root)") == 2


def test_create_uses_only_reserved_leaf_relative_to_root() -> None:
    text = _text()
    assert "type(reservation) is not ReservedManifestHandoffSupervisorControlDirectory" in text
    assert "leaf = reservation.leaf.value" in text
    assert "os.mkdir(leaf, 0o700, dir_fd=root)" in text
    assert "self._root / leaf" in text


def test_leaf_owner_mode_type_and_entry_identity_are_checked() -> None:
    text = _text()
    assert "stat.S_ISDIR(facts.st_mode)" in text
    assert "facts.st_uid == os.geteuid()" in text
    assert "stat.S_IMODE(facts.st_mode) == 0o700" in text
    assert "os.stat(leaf, dir_fd=root, follow_symlinks=False)" in text
    assert "path_facts.st_ino != child_facts.st_ino" in text


def test_new_create_fsyncs_leaf_then_root_and_retry_does_not_mutate() -> None:
    text = _text()
    assert text.index("os.fsync(child)") < text.index("os.fsync(root)")
    for forbidden in ("chmod", "chown", "replace(", "rename("):
        assert forbidden not in text


def test_resolution_reads_current_lifecycle_once_and_is_active_only() -> None:
    text = _text()
    segment = text[text.index("def resolve_active"):text.index("def _open_root")]
    assert segment.count("self._lookup(") == 1
    assert "if lifecycle is None:" in segment
    assert "type(lifecycle) is not ActiveManifestHandoffSupervisorControlDirectory" in segment
    assert segment.count("return None") == 2
    assert "os.mkdir" not in segment


def test_technical_boundary_and_no_authority_registry_or_cleanup_power() -> None:
    text = _text()
    assert "ManifestHandoffRegistryUnavailable" in text
    for forbidden in (
        "SessionPrincipal", "UserId", "WorkspaceId", "Permission", "allow:",
        "sqlalchemy", "DELETE ", "create_app", "subprocess",
    ):
        assert forbidden not in text


def test_roadmap_records_lq488_and_lq489() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-488 safe local supervisor control-directory adapter:" in roadmap
    assert "lq-488-safe-local-supervisor-control-directory-adapter.md" in roadmap
    assert "nächster Slice LQ-489" in roadmap
