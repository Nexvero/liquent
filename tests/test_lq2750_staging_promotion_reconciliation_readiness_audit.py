from pathlib import Path
import re

from tools.operational_release_bundle import EXPECTED_ENTRY_POINT_COUNT


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-2750-staging-promotion-reconciliation-readiness-audit.md"
COMMAND = "liquent-staging-promotion-reconciliation-readiness-audit"
TARGET = (
    "liquent_platform.transport."
    "staging_research_index_promotion_reconciliation_readiness_audit_cli:main"
)


def test_readiness_audit_has_one_exact_installed_entry_point() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert project.count(f'{COMMAND} = "{TARGET}"') == 1


def test_release_inventory_tracks_added_transport_command() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    scripts = re.findall(r"^liquent-[a-z0-9-]+\s*=", project, re.MULTILINE)
    operators = list((ROOT / "src/liquent_platform/operators").glob("*.py"))
    assert len(scripts) == EXPECTED_ENTRY_POINT_COUNT == 76
    assert len(operators) == 72


def test_documentation_keeps_readiness_non_authoritative_and_read_only() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert COMMAND in text
    for phrase in (
        "does not run reconciliation",
        "does not grant promotion or deployment authority",
        "no provider HTTP request",
        "no database mutation",
        "never an authorization signal",
    ):
        assert phrase in text
