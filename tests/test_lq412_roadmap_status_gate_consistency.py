from pathlib import Path
import re


ROOT = Path(__file__).parents[1]
ROADMAP = ROOT / "docs" / "technical-status-and-roadmap.md"
CONTRACT = ROOT / "docs" / "lq-412-consolidated-roadmap-status-gate-consistency.md"
PYPROJECT = ROOT / "pyproject.toml"
OPERATORS = ROOT / "src" / "liquent_platform" / "operators"
MIGRATIONS = (
    ROOT / "src" / "liquent_platform" / "persistence" / "alembic" / "versions"
)


def _roadmap_head() -> str:
    text = ROADMAP.read_text(encoding="utf-8")
    return text[: text.index("## 2. Abgeschlossene Foundations / Schritte")]


def test_consolidated_head_records_separate_verified_test_boundaries() -> None:
    head = _roadmap_head()
    assert "**7167 passed**, **111 skipped**" in head
    assert "**107 passed**, **7171 deselected**" in head
    assert "PostgreSQL-16.14-Cluster mit UTC-Sessions" in head
    assert "bis LQ-2620" in head
    assert "alle zehn kontrollierten Phasen" in head


def test_consolidated_inventory_matches_repository_files() -> None:
    project = PYPROJECT.read_text(encoding="utf-8")
    scripts = re.findall(r"^liquent-[a-z0-9-]+\s*=", project, re.MULTILINE)
    operators = [
        path for path in OPERATORS.glob("*.py") if path.name != "__init__.py"
    ]
    migrations = [
        path for path in MIGRATIONS.glob("*.py") if path.name != "__init__.py"
    ]

    assert len(scripts) == 71
    assert len(operators) == 70
    assert len(migrations) == 42

    head = _roadmap_head()
    assert "**71 Console Entry Points**, **70 Operatorimplementierungs-" in head
    assert "und Hilfsmodule** plus Paketinitialisierer" in head
    assert "**42 lineare Migrationen**, Head\n  `20260826_0042`" in head


def test_migration_head_claim_matches_the_enforced_gate() -> None:
    gate = (ROOT / "tests" / "test_persistence_migration_gate.py").read_text(
        encoding="utf-8"
    )
    assert 'expected_head() == "20260826_0042"' in gate


def test_release_boundary_and_lq412_bundle_drift_are_traceable() -> None:
    head = _roadmap_head()
    contract = CONTRACT.read_text(encoding="utf-8")
    bundle = (ROOT / "tools" / "operational_release_bundle.py").read_text(
        encoding="utf-8"
    )

    assert "externe\n  Signierung, Providerfreigabe, Staging-Akzeptanz" in head
    assert "34 Console Entry Points" in contract
    assert "38 Operatormodule" in contract
    assert "finale Packaging- und Bundle-Preflight noch nicht als bestanden" in contract
    assert "EXPECTED_ENTRY_POINT_COUNT = 71" in bundle
    assert "EXPECTED_OPERATOR_FILE_COUNT = 71" in bundle


def test_roadmap_links_lq412_and_the_next_bounded_slice() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")
    assert "- LQ-412 consolidated roadmap status and gate consistency:" in roadmap
    assert "`docs/lq-412-consolidated-roadmap-status-gate-consistency.md`" in roadmap
    assert "nächster Slice LQ-413 synchronisiert Bundleinventar" in roadmap
