import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
COMPOSITION = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_control_directory_cleanup_composition.py"


def _text() -> str:
    return COMPOSITION.read_text(encoding="utf-8")


def test_composition_requires_explicit_owned_dependencies() -> None:
    text = _text()
    assert "database_engine: Engine" in text
    assert "backend_instance_id: ManifestHandoffSupervisorBackendInstanceId" in text
    assert "control_directory_root: Path" in text
    assert "control_directory_root.is_absolute()" in text


def test_composition_exposes_retention_clearance_execution_and_reconciliation() -> None:
    tree = ast.parse(_text())
    cls = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "ManifestHandoffSupervisorControlDirectoryCleanupComposition"
    )
    slots = next(
        node for node in cls.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__slots__" for target in node.targets)
    )
    assert ast.literal_eval(slots.value) == (
        "retention_operation", "clearance_creation", "execution", "reconciliation"
    )


def test_persistent_adapters_share_one_engine_and_current_lookups() -> None:
    text = _text()
    assert text.count("DatabaseManifestHandoffSupervisorControlDirectories(") == 2
    assert "directory_lookup=directories" in text
    assert text.count("DatabaseManifestHandoffSupervisorControlDirectoryCleanup(") == 1
    assert text.count("DatabaseManifestHandoffSupervisorRuntime(") == 1
    assert text.count("DatabaseManifestHandoffSupervisorJournal(") == 1
    assert "directory_lookup=directories" in text
    assert "decision_lookup=attempts" in text
    assert "writer_journal_lookup=journal.inspect_writer_journal" in text
    assert "recovery_journal_lookup=journal.inspect_recovery_journal" in text


def test_local_boundaries_share_root_codec_and_persistent_sources() -> None:
    text = _text()
    tree = ast.parse(text)
    local_types = {
        "SafeLocalManifestHandoffSupervisorControlDirectoryCleanupPreflight",
        "SafeLocalManifestHandoffSupervisorControlDirectoryPhysicalCleanup",
        "SafeLocalManifestHandoffSupervisorControlDirectoryCleanupReconciliation",
    }
    local_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in local_types
    ]
    assert text.count("codec = CanonicalManifestHandoffSupervisorControlArtifactCodec()") == 1
    assert len(local_calls) == 3
    assert all(ast.unparse(call.args[0]) == "control_directory_root" for call in local_calls)
    assert text.count("artifact_lookup=runtime.resolve_artifact_role") == 3
    assert text.count("claim_lookup=claims.resolve_control_directory_cleanup_write_claim") == 2
    assert text.count("directory_lookup=directories.resolve_control_directory") == 2


def test_execution_and_reconciliation_use_shared_attempt_store() -> None:
    text = _text()
    assert "attempts=attempts," in text
    assert text.count("outcomes=attempts,") == 2
    assert "physical=physical," in text
    assert "physical=physical_reconciliation," in text


def test_construction_is_inert_and_has_no_automatic_activation_surface() -> None:
    text = _text()
    tree = ast.parse(text)
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "compose_manifest_handoff_supervisor_control_directory_cleanup"
    )
    calls = [ast.unparse(node.func) for node in ast.walk(function) if isinstance(node, ast.Call)]
    for forbidden in (
        "create_control_directory_cleanup_clearance",
        "execute",
        "cleanup_control_directory",
        "reconcile_control_directory_cleanup",
        "create_app",
        "dispose",
        "mkdir",
    ):
        assert forbidden not in calls
    for forbidden in ("schedule", "batch", "worker", "route", "lifespan", "os.environ"):
        assert forbidden not in text.lower()


def test_build_failures_are_detail_free() -> None:
    text = _text()
    assert "except ManifestHandoffRegistryUnavailable:" in text
    assert "except Exception:" in text
    assert "raise ManifestHandoffRegistryUnavailable from None" in text


def test_roadmap_records_lq517_and_lq518() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-517 explicit opt-in supervisor control-directory cleanup composition:" in roadmap
    assert "lq-517-explicit-opt-in-supervisor-control-directory-cleanup-composition.md" in roadmap
    assert "nächster Slice LQ-518" in roadmap
