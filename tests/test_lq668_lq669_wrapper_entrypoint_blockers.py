import ast
import importlib
from pathlib import Path


ROOT = Path(__file__).parents[1]
PYPROJECT = ROOT / "pyproject.toml"
CHILD = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_child_process.py"
CANDIDATE = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_candidate_composition.py"
EXECUTOR = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_capability_executor.py"
ARTIFACTS = ROOT / "src/liquent_platform/transport/manifest_handoff_supervisor_control_artifacts.py"


def test_capability_primitives_are_now_inside_the_installable_package_root():
    project = PYPROJECT.read_text(encoding="utf-8")
    assert 'where = ["src"]' in project
    for name in (
        "private_manifest_handoff.py",
        "pre_staging_manifest.py",
        "private_manifest_handoff_reconcile.py",
    ):
        assert (ROOT / "src/liquent_platform/capabilities" / name).is_file()


def test_tools_compatibility_names_alias_the_exact_package_modules():
    for name in (
        "private_manifest_handoff",
        "pre_staging_manifest",
        "private_manifest_handoff_reconcile",
    ):
        compatibility = importlib.import_module(f"tools.{name}")
        packaged = importlib.import_module(f"liquent_platform.capabilities.{name}")
        assert compatibility is packaged


def test_exact_writer_and_recovery_wrapper_scripts_are_now_registered():
    project = PYPROJECT.read_text(encoding="utf-8")
    assert project.count("liquent-supervisor-writer-wrapper =") == 1
    assert project.count("liquent-supervisor-recovery-wrapper =") == 1
    assert "manifest_handoff_supervisor_child:writer_main" in project
    assert "manifest_handoff_supervisor_child:recovery_main" in project


def test_child_and_candidate_are_not_misrepresented_as_process_entrypoints():
    for path in (CHILD, CANDIDATE):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        functions = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
        assert "main" not in functions
        assert '__name__ == "__main__"' not in path.read_text(encoding="utf-8")


def test_existing_executor_only_delegates_to_injected_primitives():
    text = EXECUTOR.read_text(encoding="utf-8")
    assert "self._writer.release_writer(" in text
    assert "self._recovery.release_recovery(" in text
    for forbidden in ("handoff_manifest", "reconcile_manifest_handoff", "subprocess"):
        assert forbidden not in text


def test_installable_capabilities_never_import_repository_tools():
    root = ROOT / "src/liquent_platform/capabilities"
    for path in root.glob("*.py"):
        assert "from tools" not in path.read_text(encoding="utf-8")


def test_host_control_adapter_requires_root_and_resolved_child_directory():
    text = ARTIFACTS.read_text(encoding="utf-8")
    assert "path.parent != self._root" in text
    assert "os.open(path.name" in text
    assert "dir_fd=root" in text


def test_candidate_readiness_stays_closed_until_all_prerequisites_exist():
    text = CANDIDATE.read_text(encoding="utf-8")
    assert "production_ready: bool = field(default=False, init=False)" in text
