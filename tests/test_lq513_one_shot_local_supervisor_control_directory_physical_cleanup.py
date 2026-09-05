import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "src/liquent_platform/transport/manifest_handoff_supervisor_control_directory_physical_cleanup.py"


def _text() -> str:
    return ADAPTER.read_text(encoding="utf-8")


def test_adapter_has_only_one_physical_public_effect() -> None:
    tree = ast.parse(_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    methods = {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}
    assert "remove_control_directory" in methods
    assert not {"retry", "resume", "continue_cleanup", "reconcile", "prepare"} & methods


def test_only_full_persistent_claim_and_retired_target_open_access() -> None:
    text = _text()
    assert "type(claimed) is not ClaimedManifestHandoffSupervisorControlDirectoryCleanup" in text
    assert "current = self._claims(claimed.attempt_id)" in text
    assert "type(current) is not ClaimedManifestHandoffSupervisorControlDirectoryCleanup" in text
    assert "current != claimed" in text
    assert "retired = self._directories(claimed.directory_id)" in text
    assert "type(retired) is not RetiredManifestHandoffSupervisorControlDirectory" in text


def test_root_and_exact_retired_leaf_are_private_descriptor_bound() -> None:
    text = _text()
    assert "os.lstat(self._root)" in text
    assert "os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC" in text
    assert "leaf_name = retired.leaf.value" in text
    assert "os.open(leaf_name, _OPEN_DIRECTORY, dir_fd=root)" in text
    assert "stat.S_IMODE(facts.st_mode) == 0o700" in text
    assert "entry.st_dev == facts.st_dev" in text
    assert "entry.st_ino == facts.st_ino" in text


def test_all_artifacts_and_names_are_revalidated_before_each_unlink() -> None:
    text = _text()
    start = text.index("for role in _ROLES:", text.index("def remove_control_directory"))
    loop = text[start:text.index("del remaining[filename]", start)]
    assert "canonical_manifest_handoff_supervisor_control_artifact_name(role)" in loop
    assert "self._current_matches(claimed, retired, artifacts)" in loop
    assert "self._inventory(root, leaf_name, leaf, remaining)" in loop
    assert "self._matches_artifact(leaf, filename, remaining[filename])" in loop


def test_files_are_again_private_single_link_bounded_and_canonical() -> None:
    text = _text()
    assert "os.open(name, _OPEN_FILE, dir_fd=directory)" in text
    assert "stat.S_ISREG(facts.st_mode)" in text
    assert "stat.S_IMODE(facts.st_mode) == 0o600" in text
    assert "facts.st_nlink == 1" in text
    assert "remaining = _MAX_BYTES + 1" in text
    assert "document = self._codec.decode_content(content)" in text
    assert "encoded.facts == record.facts" in text
    assert "encoded.content.value == content" in text


def test_effects_are_relative_ordered_and_each_file_is_durable() -> None:
    text = _text()
    section = text[text.index("effect_started = True\n                os.unlink"):
                   text.index("del remaining[filename]")]
    assert "os.unlink(filename, dir_fd=leaf)" in section
    assert section.index("os.unlink") < section.index("os.fsync(leaf)")
    assert "os.rmdir(leaf_name, dir_fd=root)" in text
    assert text.index("os.rmdir(leaf_name, dir_fd=root)") < text.index("os.fsync(root)")


def test_leaf_is_empty_and_revalidated_before_rmdir() -> None:
    text = _text()
    rmdir = text.index("os.rmdir(leaf_name, dir_fd=root)")
    before = text[:rmdir]
    assert "if remaining or self._names(leaf) or not self._safe_leaf" in before
    assert before.rindex("self._current_matches(claimed, retired, artifacts)") < rmdir


def test_removed_requires_confirmed_absence_root_and_monotone_time() -> None:
    text = _text()
    section = text[text.index("os.rmdir(leaf_name, dir_fd=root)"):
                   text.index("return RemovedManifestHandoffSupervisorControlDirectory")]
    assert "os.fsync(root)" in section
    assert "os.stat(leaf_name, dir_fd=root, follow_symlinks=False)" in section
    assert "except FileNotFoundError" in section
    assert "self._same_root(root)" in section
    assert "self._now(claimed.claimed_at)" in section


def test_every_failure_after_effect_threshold_becomes_unknown() -> None:
    text = _text()
    assert "effect_started = False" in text
    assert text.count("effect_started = True") == 2
    assert "if effect_started:\n                return self._unknown(claimed)" in text
    assert "UnknownManifestHandoffSupervisorControlDirectoryCleanupEffect(" in text
    assert "claimed.claim_id, claimed.attempt_id, claimed.directory_id" in text
    assert "except OSError:\n            pass" in text


def test_no_recursive_free_path_repair_persistence_or_wiring_power() -> None:
    text = _text()
    for forbidden in (
        "rmtree", "glob(", "subprocess", "os.system", "os.chdir", "os.mkdir",
        "os.link", "os.rename", "os.replace", "chmod", "chown", "truncate",
        "sqlalchemy", "INSERT ", "UPDATE ", "DELETE ", "SessionPrincipal",
        "WorkspaceId", "Permission", "create_app",
    ):
        assert forbidden not in text


def test_roadmap_records_lq513_and_lq514() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-513 one-shot local supervisor control-directory physical cleanup:" in roadmap
    assert "lq-513-one-shot-local-supervisor-control-directory-physical-cleanup.md" in roadmap
    assert "nächster Slice LQ-514" in roadmap
