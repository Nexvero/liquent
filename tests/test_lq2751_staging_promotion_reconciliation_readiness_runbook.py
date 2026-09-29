from pathlib import Path


ROOT = Path(__file__).parents[1]
RUNBOOK = ROOT / "operations/runbooks/staging-promotion.md"
DOC = (
    ROOT
    / "docs/lq-2751-staging-promotion-reconciliation-readiness-runbook-and-completion-audit.md"
)
COMMAND = "liquent-staging-promotion-reconciliation-readiness-audit"


def _readiness_section() -> str:
    text = RUNBOOK.read_text(encoding="utf-8")
    start = text.index("### Audit reconciliation readiness")
    end = text.index("This is a separate, manual recovery action", start)
    return text[start:end]


def test_runbook_orders_readiness_between_installation_and_reconciliation() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    install = text.index("### Install reconciliation settings")
    readiness = text.index("### Audit reconciliation readiness")
    reconcile = text.index("liquent-staging-promotion-reconcile /ABSOLUTE/PROCESS_SETTINGS")
    assert install < readiness < reconcile


def test_runbook_uses_exact_command_and_closed_results() -> None:
    section = _readiness_section()
    assert f"{COMMAND} /ABSOLUTE/PROCESS_SETTINGS" in section
    for token, code in (
        ("`ready`", "`0`"),
        ("`unavailable`", "`1`"),
        ("`invalid_invocation`", "`2`"),
    ):
        assert token in section
        assert code in section
    assert "do not retry automatically" in section
    assert "do not invoke reconciliation" in section


def test_runbook_preserves_read_only_non_authorizing_boundary() -> None:
    section = _readiness_section()
    assert "makes no provider request" in section
    assert "no reconciliation or database\nmutation" in section
    assert "grants no promotion or deployment authority" in section
    assert "prerequisite evidence only" in section
    assert "settings paths, values, endpoint, database URL" in section


def test_completion_audit_binds_packaging_runbook_and_external_decision() -> None:
    text = DOC.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    runbook = RUNBOOK.read_text(encoding="utf-8")
    assert COMMAND in text and COMMAND in project and COMMAND in runbook
    assert "LQ-2750" in text and "LQ-2751" in text
    assert (
        "after settings installation and before any independent reconciliation "
        "decision" in normalized
    )
    assert "neither proves that an unknown attempt exists" in normalized
    assert "closes only the manual read-only preflight" in normalized
    assert "does not close or automate" in normalized
