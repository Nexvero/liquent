import ast
from pathlib import Path

ROOT=Path(__file__).parents[1]
COMPOSITION=ROOT/"src/liquent_platform/application/manifest_handoff_supervisor_composition.py"
def _text(): return COMPOSITION.read_text(encoding="utf-8")

def test_factory_has_only_explicit_controlled_dependencies():
    tree=ast.parse(_text())
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef))
    names=[argument.arg for argument in function.args.kwonlyargs]
    assert names == ["database_engine","backend_instance_id","supervisor_engine",
        "control_artifacts","capability_executor","capability_outcomes","clock"]

def test_one_shared_journal_runtime_and_gate_adapter_are_built():
    text=_text()
    assert text.count("DatabaseManifestHandoffSupervisorJournal(") == 1
    assert text.count("DatabaseManifestHandoffSupervisorRuntime(") == 1
    assert text.count("DatabaseManifestHandoffSupervisorGateBindings(") == 1
    assert "runtime_bindings=runtime, control_artifacts=runtime" in text

def test_one_codec_and_wrapper_share_control_artifact_boundary():
    text=_text()
    assert text.count("CanonicalManifestHandoffSupervisorControlArtifactCodec()") == 1
    assert "codec=codec, publisher=control_artifacts, reader=control_artifacts" in text

def test_all_five_slices_feed_the_facade():
    text=_text()
    for name in ("Prepare","Release","Inspect","Terminal","Terminate"):
        assert f"PersistentManifestHandoffSupervisor{name}Service(" in text
    assert "return PersistentManifestHandoffSupervisorService(" in text
    assert "prepare=prepare, release=release, inspect=inspect" in text
    assert "terminate=terminate, terminal=terminal" in text

def test_clock_is_shared_but_not_required():
    text=_text()
    assert "clock: Callable[[], datetime] | None = None" in text
    assert text.count("clock=clock") >= 4

def test_factory_has_no_activation_migration_file_or_lifecycle_effect():
    text=_text()
    for forbidden in ("create_app","add_route","migrate","upgrade(","create_all",
            "Path","open(","mkdir","Thread","Worker","dispose(","close(","os.environ"):
        assert forbidden not in text

def test_no_authority_or_caller_allow_input():
    text=_text()
    for forbidden in ("SessionPrincipal","UserId","WorkspaceId","Permission","allow"):
        assert forbidden not in text

def test_roadmap_records_lq481_and_lq482():
    roadmap=(ROOT/"docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-481 controlled persistent supervisor dependency composition:" in roadmap
    assert "lq-481-controlled-persistent-supervisor-dependency-composition.md" in roadmap
    assert "nächster Slice LQ-482" in roadmap
