from pathlib import Path
import re

from tools.operational_release_bundle import EXPECTED_ENTRY_POINT_COUNT


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-2752-staging-promotion-reconciliation-candidate-audit.md"
RUNBOOK = ROOT / "operations/runbooks/staging-promotion.md"
COMMAND = "liquent-staging-promotion-reconciliation-candidate-audit"
TARGET = (
    "liquent_platform.transport."
    "staging_research_index_promotion_reconciliation_candidate_audit_cli:main"
)


def test_candidate_audit_has_one_exact_installed_entry_point() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert project.count(f'{COMMAND} = "{TARGET}"') == 1


def test_release_inventory_tracks_added_transport_command() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    scripts = re.findall(r"^liquent-[a-z0-9-]+\s*=", project, re.MULTILINE)
    operators = list((ROOT / "src/liquent_platform/operators").glob("*.py"))
    assert len(scripts) == EXPECTED_ENTRY_POINT_COUNT == 76
    assert len(operators) == 72


def test_documentation_keeps_candidate_audit_non_authoritative() -> None:
    text = DOC.read_text(encoding="utf-8")
    for phrase in (
        COMMAND,
        "does not expose the operation identity",
        "does not run reconciliation",
        "no provider HTTP request",
        "no database mutation",
        "never an authorization signal",
    ):
        assert phrase in text


def test_runbook_orders_candidate_audit_before_reconciliation() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    readiness = text.index("### Audit reconciliation readiness")
    candidate = text.index("### Audit an eligible reconciliation candidate")
    reconcile = text.index(
        "liquent-staging-promotion-reconcile /ABSOLUTE/PROCESS_SETTINGS"
    )
    assert readiness < candidate < reconcile
    section = text[candidate:reconcile]
    assert f"{COMMAND} /ABSOLUTE/PROCESS_SETTINGS" in section
    for token, code in (
        ("`pending`", "`0`"),
        ("`idle`", "`0`"),
        ("`unavailable`", "`1`"),
        ("`invalid_invocation`", "`2`"),
    ):
        assert token in section and code in section
    assert "never exposes an operation\nidentity" in section
    assert "grants no reconciliation, promotion or deployment authority" in section
