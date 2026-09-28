import importlib
from pathlib import Path

from liquent_platform.capabilities import pre_staging_manifest
from liquent_platform.capabilities import private_manifest_handoff
from liquent_platform.capabilities import private_manifest_handoff_reconcile


ROOT = Path(__file__).parents[1]


def test_all_three_capabilities_resolve_below_the_installable_source_package():
    package = ROOT / "src/liquent_platform/capabilities"
    for module in (
        pre_staging_manifest,
        private_manifest_handoff,
        private_manifest_handoff_reconcile,
    ):
        assert Path(module.__file__).parent == package


def test_compatibility_imports_are_module_identity_aliases_not_copies():
    names = (
        "pre_staging_manifest",
        "private_manifest_handoff",
        "private_manifest_handoff_reconcile",
    )
    for name in names:
        assert importlib.import_module(f"tools.{name}") is importlib.import_module(
            f"liquent_platform.capabilities.{name}"
        )


def test_package_dependency_direction_is_internal_and_acyclic():
    renderer = Path(pre_staging_manifest.__file__).read_text(encoding="utf-8")
    writer = Path(private_manifest_handoff.__file__).read_text(encoding="utf-8")
    recovery = Path(private_manifest_handoff_reconcile.__file__).read_text(
        encoding="utf-8"
    )
    assert "private_manifest_handoff" not in renderer
    assert "liquent_platform.capabilities.pre_staging_manifest" in writer
    assert "liquent_platform.capabilities.private_manifest_handoff" in recovery
    assert "from tools" not in renderer + writer + recovery


def test_application_no_longer_depends_on_repository_tools_namespace():
    source = (
        ROOT / "src/liquent_platform/application/manifest_handoff.py"
    ).read_text(encoding="utf-8")
    assert "liquent_platform.capabilities.private_manifest_handoff" in source
    assert "liquent_platform.capabilities.private_manifest_handoff_reconcile" in source
    assert "from tools" not in source


def test_tools_files_are_thin_aliases_without_capability_algorithms():
    for name in (
        "pre_staging_manifest.py",
        "private_manifest_handoff.py",
        "private_manifest_handoff_reconcile.py",
    ):
        text = (ROOT / "tools" / name).read_text(encoding="utf-8")
        assert "sys.modules[__name__] = _implementation" in text
        assert len(text.splitlines()) <= 15
