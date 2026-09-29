from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-2761-staging-reconciliation-exercise-authorization-handoff.md"
RUNBOOK = ROOT / "operations/runbooks/staging-promotion.md"


def test_handoff_starts_from_the_closed_acceptance_strand() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "closed LQ-2760 acceptance evidence" in text
    assert "one future staging reconciliation exercise" in text
    assert "decision checklist, not an approval record" in text
    assert "does not authorize\nsettings installation" in text


def test_handoff_requires_one_complete_current_decision_packet() -> None:
    text = DOC.read_text(encoding="utf-8")
    for phrase in (
        "Exact staging boundary",
        "Owner-private settings custody",
        "Current provider authorization",
        "Current PostgreSQL readiness",
        "Current durable state",
        "Named decision roles",
        "Bounded exercise window",
        "`approved`, `rejected` or `expired`",
    ):
        assert phrase in text
    assert "Approval expires before any later run and cannot be reused" in text


def test_handoff_binds_the_existing_manual_command_order() -> None:
    text = DOC.read_text(encoding="utf-8")
    runbook = RUNBOOK.read_text(encoding="utf-8")
    commands = (
        "liquent-staging-promotion-reconciliation-settings-install",
        "liquent-staging-promotion-reconciliation-readiness-audit",
        "liquent-staging-promotion-reconciliation-candidate-audit",
        "liquent-staging-promotion-reconcile",
    )
    positions = [text.index(command) for command in commands]
    assert positions == sorted(positions)
    for command in commands:
        assert command in runbook
    assert "Reconciliation exercise authorization handoff" in runbook
    assert "Approval is valid for one bounded exercise\nwindow" in runbook


def test_handoff_is_fail_closed_and_exposes_no_secret_material() -> None:
    text = DOC.read_text(encoding="utf-8")
    runbook = RUNBOOK.read_text(encoding="utf-8")
    assert "Stop without a provider request or reconciliation" in text
    assert "settings tamper,\ndatabase unavailability, schema mismatch" in text
    assert "There is no automatic retry, loop, polling, bulk drain" in text
    assert "must contain no settings path or\nvalue, endpoint, database URL" in runbook
    assert "adds documentation and tests only" in text
    assert "does\nnot perform or authorize the real staging exercise" in text
