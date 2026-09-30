from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-2766-staging-reconciliation-exercise-completion-audit.md"
RUNBOOK = ROOT / "operations/runbooks/staging-promotion.md"


def test_completion_audit_binds_the_full_ordered_evidence_chain() -> None:
    text = DOC.read_text(encoding="utf-8")
    for number in range(2761, 2766):
        documents = list((ROOT / "docs").glob(f"lq-{number}-*.md"))
        assert len(documents) == 1
        assert f"LQ-{number}" in text
    assert "LQ-2761 through LQ-2765" in text
    assert (
        "authorization_handoff -> decision_packet -> decision_validation ->\n"
        "outcome_packet -> outcome_validation"
    ) in text


def test_completion_audit_has_fixed_fail_closed_terminal_states() -> None:
    text = DOC.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    for result in ("`complete`", "`stopped`", "`unverified`", "`invalid`"):
        assert result in text
    assert "result: complete|stopped|unverified|invalid" in text
    assert "does not mean that reconciliation succeeded" in normalized
    assert "correctly stopped exercise can be complete" in normalized
    assert "never upgraded to `complete`" in normalized


def test_completion_audit_minimizes_and_preserves_private_evidence() -> None:
    text = DOC.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    assert "contains no packet value, timestamp, path, endpoint" in normalized
    assert "underlying packets and validation records remain immutable" in normalized
    assert "does not repair, normalize, combine, replay or consume a packet" in normalized
    assert "missing LQ-2761 through LQ-2765 artifact" in normalized


def test_completion_audit_preserves_closed_authority_and_external_work() -> None:
    text = DOC.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    assert "No step invokes the next step" in text
    assert "There is no fallback success, automatic retry, polling" in normalized
    assert "requires current owner-private settings" in normalized
    assert "Execution, monitoring, incident handling, promotion approval" in normalized
    assert "creates no parser, auditor, command, writer" in normalized
    assert "neither executes nor authorizes a staging reconciliation" in normalized


def test_runbook_links_completion_audit_after_outcome_validation() -> None:
    runbook = RUNBOOK.read_text(encoding="utf-8")
    normalized = " ".join(runbook.split())
    outcome = "lq-2765-staging-reconciliation-exercise-outcome-packet-validation.md"
    completion = "lq-2766-staging-reconciliation-exercise-completion-audit.md"
    assert outcome in runbook
    assert completion in runbook
    assert runbook.index(outcome) < runbook.index(completion)
    assert "Audit the closed evidence chain once" in normalized
    assert "does not prove reconciliation success" in normalized
    assert "does not authorize a new exercise" in normalized
