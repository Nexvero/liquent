from __future__ import annotations

import ast
import importlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESEARCH_ROOT = ROOT / "src" / "liquent"
PLATFORM_ROOT = ROOT / "src" / "liquent_platform"

PLATFORM_PACKAGES = (
    "liquent_platform",
    "liquent_platform.application",
    "liquent_platform.audit",
    "liquent_platform.evidence",
    "liquent_platform.identity",
    "liquent_platform.jobs",
    "liquent_platform.observability",
    "liquent_platform.persistence",
    "liquent_platform.strategy_lifecycle",
    "liquent_platform.transport",
    "liquent_platform.transport.http",
    "liquent_platform.workspace",
)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _imports_below(root: Path) -> dict[Path, set[str]]:
    return {path: _imports(path) for path in root.rglob("*.py")}


def test_platform_foundation_packages_are_importable() -> None:
    for package in PLATFORM_PACKAGES:
        assert importlib.import_module(package)


def test_research_core_does_not_depend_on_platform_or_frameworks() -> None:
    forbidden_roots = {
        "alembic",
        "fastapi",
        "flask",
        "pydantic",
        "sqlalchemy",
        "starlette",
        "uvicorn",
    }
    for path, names in _imports_below(RESEARCH_ROOT).items():
        roots = {name.split(".", 1)[0] for name in names}
        assert "liquent_platform" not in roots, path
        assert not roots.intersection(forbidden_roots), path


def test_application_and_capabilities_do_not_import_adapters() -> None:
    protected = (
        PLATFORM_ROOT / "application",
        PLATFORM_ROOT / "audit",
        PLATFORM_ROOT / "evidence",
        PLATFORM_ROOT / "identity",
        PLATFORM_ROOT / "jobs",
        PLATFORM_ROOT / "strategy_lifecycle",
        PLATFORM_ROOT / "workspace",
    )
    forbidden = (
        "liquent_platform.persistence",
        "liquent_platform.transport",
        "fastapi",
        "sqlalchemy",
    )
    for root in protected:
        for path, names in _imports_below(root).items():
            if path.name.endswith("_composition.py"):
                continue
            names.discard("liquent_platform.persistence.identity_errors")
            assert not any(
                name == prefix or name.startswith(f"{prefix}.")
                for name in names
                for prefix in forbidden
            ), path


def test_http_transport_has_no_direct_research_or_paper_dependency() -> None:
    forbidden = ("liquent.backtesting", "liquent.bot", "liquent.risk", "liquent.strategy")
    for path, names in _imports_below(PLATFORM_ROOT / "transport" / "http").items():
        assert not any(
            name == prefix or name.startswith(f"{prefix}.")
            for name in names
            for prefix in forbidden
        ), path


def test_platform_has_no_trading_connectivity_modules() -> None:
    forbidden_parts = {"broker", "exchange", "live_trading", "paper_trading"}
    for path in PLATFORM_ROOT.rglob("*.py"):
        assert forbidden_parts.isdisjoint(path.parts), path
