import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "src/liquent_platform/transport/manifest_handoff_supervisor_control_artifacts.py"


def _text() -> str:
    return ADAPTER.read_text(encoding="utf-8")


def _methods(name: str) -> set[str]:
    tree = ast.parse(_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name)
    return {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}


def test_codec_is_versioned_canonical_and_duplicate_strict() -> None:
    text = _text()
    assert '_SCHEMA = "liquent.manifest-handoff-control"' in text
    assert "_VERSION = 1" in text
    assert 'sort_keys=True, separators=(",", ":")' in text
    assert "ensure_ascii=True, allow_nan=False" in text
    assert "object_pairs_hook=self._unique" in text
    assert "if key in result: raise ManifestHandoffRegistryUnavailable" in text


def test_decode_requires_exact_keys_and_byte_round_trip() -> None:
    text = _text()
    assert "if set(value) != keys" in text
    assert "if self.encode(result).content.value != content" in text
    assert "self.encode(document).content != artifact.content" in text
    assert "type(value.get(\"version\")) is not int" in text


def test_terminal_outcomes_are_closed_and_revalidated() -> None:
    text = _text()
    assert '"process": "writer" if writer else "recovery"' in text
    assert "CompletedManifestHandoffWriterProcess(" in text
    assert "CompletedManifestHandoffRecoveryProcess(" in text
    assert "ManifestHandoffFacts(" in text
    assert "set(facts_value) == {\"manifest_sha256\", \"file_count\"}" in text


def test_root_and_job_directory_use_no_follow_descriptors() -> None:
    text = _text()
    assert "os.open(self._root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)" in text
    assert "os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)" in text
    assert "path.parent != self._root" in text
    assert "stat.S_IMODE(facts.st_mode) != 0o700" in text


def test_publish_is_full_fsync_no_replace_and_directory_durable() -> None:
    text = _text()
    assert "os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600" in text
    assert "self._write_all(temporary_fd, request.artifact.content.value); os.fsync(temporary_fd)" in text
    assert "os.link(temporary, final" in text and "follow_symlinks=False" in text
    assert "os.unlink(temporary, dir_fd=descriptor); temporary = None" in text
    assert "os.fsync(descriptor)" in text
    assert "os.replace" not in text and "os.rename" not in text


def test_existing_and_racing_retry_compare_complete_bytes() -> None:
    text = _text()
    assert "if current != request.artifact.content.value" in text
    assert "except FileExistsError" in text
    assert "return ManifestHandoffSupervisorControlArtifactConflict()" in text
    assert text.count("return self._published(request)") >= 3


def test_read_is_bounded_regular_private_single_link() -> None:
    text = _text()
    assert "os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory" in text
    assert "not stat.S_ISREG(facts.st_mode)" in text
    assert "stat.S_IMODE(facts.st_mode) != 0o600" in text
    assert "facts.st_nlink != 1" in text
    assert "remaining=65_537" in text
    assert "except FileNotFoundError: return None" in text


def test_adapter_surface_has_no_cleanup_authority_or_process_power() -> None:
    methods = _methods("AtomicLocalManifestHandoffSupervisorControlArtifacts")
    assert {"publish", "read"} <= methods
    assert not {"remove", "delete", "cleanup", "overwrite"} & methods
    text = _text()
    for forbidden in ("SessionPrincipal", "subprocess", "Popen", "import docker", "socket", "allow:"):
        assert forbidden not in text


def test_roadmap_records_lq464_and_next_wrapper_contract() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-464 canonical control artifact codec and atomic local file adapter:" in roadmap
    assert "lq-464-canonical-control-artifact-codec-and-atomic-local-file-adapter.md" in roadmap
    assert "nächster Slice LQ-465" in roadmap
