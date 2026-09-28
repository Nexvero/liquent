from pathlib import Path
import re

from tools.operational_release_bundle import EXPECTED_ENTRY_POINT_COUNT


ROOT = Path(__file__).parents[1]
COMMAND = "liquent-staging-promotion-reconcile"
TARGET = (
    "liquent_platform.transport."
    "staging_research_index_promotion_reconciliation_cli:main"
)


def test_reconciliation_cli_has_one_exact_installed_entry_point() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    expected = f'{COMMAND} = "{TARGET}"'
    assert project.count(expected) == 1


def test_release_inventory_tracks_the_added_command_without_operator_drift() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    scripts = re.findall(r"^liquent-[a-z0-9-]+\s*=", project, re.MULTILINE)
    operators = list((ROOT / "src/liquent_platform/operators").glob("*.py"))
    assert len(scripts) == EXPECTED_ENTRY_POINT_COUNT == 74
    assert len(operators) == 72


def test_entry_point_targets_the_existing_detail_free_cli_boundary() -> None:
    module = (
        ROOT
        / "src/liquent_platform/transport"
        / "staging_research_index_promotion_reconciliation_cli.py"
    ).read_text(encoding="utf-8")
    assert "def main() -> None:" in module
    assert 'stderr.write("unavailable\\n")' in module
    assert "retry" not in module.lower()
