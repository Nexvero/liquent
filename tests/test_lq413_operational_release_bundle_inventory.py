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


def test_named_wheel_inventory_matches_the_repository() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    scripts = re.findall(r"^liquent-[a-z0-9-]+\s*=", project, re.MULTILINE)
    operator_files = list((ROOT / "src/liquent_platform/operators").glob("*.py"))
    migration_files = list(
        (ROOT / "src/liquent_platform/persistence/alembic/versions").glob("*.py")
    )

    assert EXPECTED_ENTRY_POINT_COUNT == len(scripts) == 71
    assert EXPECTED_OPERATOR_FILE_COUNT == len(operator_files) == 71
    assert EXPECTED_MIGRATION_COUNT == len(migration_files) == 42


def test_required_runbook_inventory_is_complete_and_exact() -> None:
    actual = {
        path.name for path in (ROOT / "operations/runbooks").glob("*.md")
    }
    assert len(RUNBOOKS) == 17
    assert set(RUNBOOKS) == actual


def test_every_required_contract_exists_as_a_regular_file() -> None:
    assert len(CONTRACTS) == len(set(CONTRACTS))
    assert all((ROOT / "docs" / name).is_file() for name in CONTRACTS)
    assert {
        "lq-491-retired-supervisor-control-directory-retention-and-cleanup-contract.md",
        "lq-518-owner-controlled-single-supervisor-control-directory-cleanup-operator-contract.md",
        "lq-522-supervisor-control-directory-cleanup-end-to-end-readiness-audit.md",
    } <= set(CONTRACTS)


def test_bundle_uses_named_fail_closed_inventory_limits() -> None:
    source = (ROOT / "tools/operational_release_bundle.py").read_text(
        encoding="utf-8"
    )
    assert "len(entry_points) != EXPECTED_ENTRY_POINT_COUNT" in source
    assert "len(operators) != EXPECTED_OPERATOR_FILE_COUNT" in source
    assert "len(migrations) != EXPECTED_MIGRATION_COUNT" in source
    assert "len(entry_points) != 34" not in source
    assert "len(operators) != 38" not in source


def test_roadmap_links_the_synchronized_slice_and_bounded_preflight() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(
        encoding="utf-8"
    )
    assert "- LQ-413 operational release bundle inventory synchronization:" in roadmap
    assert "`docs/lq-413-operational-release-bundle-inventory-synchronization.md`" in roadmap
    assert "nächster Slice LQ-414 führt den lokalen Packaging-" in roadmap
