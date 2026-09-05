from pathlib import Path
import re

from tools.operational_release_bundle import (
    CONTRACTS,
    EXPECTED_ENTRY_POINT_COUNT,
    EXPECTED_MIGRATION_COUNT,
    EXPECTED_OPERATOR_FILE_COUNT,
    RUNBOOKS,
)


ROOT = Path(__file__).parents[1]


def test_named_inventory_exactly_matches_current_source() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    scripts = re.findall(r"^liquent-[a-z0-9-]+\s*=", project, re.MULTILINE)
    operators = list((ROOT / "src/liquent_platform/operators").glob("*.py"))
    migrations = list(
        (ROOT / "src/liquent_platform/persistence/alembic/versions").glob("*.py")
    )
    assert len(scripts) == EXPECTED_ENTRY_POINT_COUNT == 71
    assert len(operators) == EXPECTED_OPERATOR_FILE_COUNT == 71
    assert len(migrations) == EXPECTED_MIGRATION_COUNT == 42


def test_cleanup_entry_point_is_unique_and_separate() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    entry = (
        'liquent-supervisor-control-directory-cleanup = '
        '"liquent_platform.operators.manifest_handoff_supervisor_control_directory_cleanup:main"'
    )
    assert project.count(entry) == 1


def test_three_cleanup_contracts_are_required_exactly_once() -> None:
    expected = {
        "lq-491-retired-supervisor-control-directory-retention-and-cleanup-contract.md",
        "lq-518-owner-controlled-single-supervisor-control-directory-cleanup-operator-contract.md",
        "lq-522-supervisor-control-directory-cleanup-end-to-end-readiness-audit.md",
    }
    assert expected <= set(CONTRACTS)
    assert len(CONTRACTS) == len(set(CONTRACTS))
    assert all((ROOT / "docs" / name).is_file() for name in expected)


def test_runbook_inventory_remains_closed_and_unchanged() -> None:
    actual = {path.name for path in (ROOT / "operations/runbooks").glob("*.md")}
    assert len(RUNBOOKS) == 17
    assert set(RUNBOOKS) == actual
    assert not any("supervisor" in name and "cleanup" in name for name in RUNBOOKS)


def test_synthetic_wheel_fixture_uses_current_linear_migration_inventory() -> None:
    fixture = (ROOT / "tests/test_operational_release_bundle.py").read_text(
        encoding="utf-8"
    )
    assert "for index in range(42):" in fixture
    assert 'revision = f"20260826_{index + 1:04d}"' in fixture
    assert 'f"20260826_{index:04d}"' in fixture
    assert '"migration_head": "20260826_0042"' in fixture
    assert "range(27)" not in fixture


def test_inventory_sync_changes_no_runtime_or_operator_source() -> None:
    document = (
        ROOT / "docs/lq-523-supervisor-cleanup-operational-release-inventory-synchronization.md"
    ).read_text(encoding="utf-8")
    assert "keine Änderung an Operatorcode, Appfactory, Lifespan" in document
    assert "nicht production-ready" in document


def test_roadmap_records_lq523_and_lq524() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-523 supervisor cleanup operational release inventory synchronization:" in roadmap
    assert "lq-523-supervisor-cleanup-operational-release-inventory-synchronization.md" in roadmap
    assert "nächster Slice LQ-524" in roadmap
