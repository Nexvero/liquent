from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-2765-staging-reconciliation-exercise-outcome-packet-validation.md"
RUNBOOK = ROOT / "operations/runbooks/staging-promotion.md"


def test_validation_is_manual_completion_evidence_only() -> None:
    text = DOC.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    assert "manual validation boundary for one completed LQ-2764" in normalized
    assert "recorded consistently and closed" in normalized
    assert "does not turn the outcome packet into a credential" in normalized
    assert "No packet value is copied into a ticket, command line, log" in normalized


def test_validation_is_ordered_complete_and_non_repairing() -> None:
    text = DOC.read_text(encoding="utf-8")
    headings = (
        "**Shape**",
        "**Tokens**",
        "**Command sequence**",
        "**Durable evidence**",
        "**Result consistency**",
        "**Closure**",
    )
    positions = [text.index(heading) for heading in headings]
    assert positions == sorted(positions)
    assert "stop at the first failed step" in text
    assert "Do not repair, infer, normalize or complete an outcome packet" in text
    assert "Do not re-run a command to make the packet pass" in text


def test_validation_checks_closed_sequence_and_result_consistency() -> None:
    text = DOC.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    assert "after the first stop-boundary result, every later command is `not_run`" in normalized
    assert "`completed` appears only with `reconciled` from both reconciliation" in normalized
    assert "known non-completion is `stopped`" in normalized
    assert "any mismatch, missing fact or unavailable inspection is `unverified`" in normalized
    assert "decision packet is recorded as consumed" in normalized


def test_validation_has_fixed_data_minimizing_results() -> None:
    text = DOC.read_text(encoding="utf-8")
    for result in ("`valid`", "`invalid`", "`unverified`"):
        assert result in text
    assert "result: valid|invalid|unverified" in text
    assert "contains no packet value, reason detail, path, endpoint" in text
    assert "`valid` is completion evidence" in text


def test_validation_fails_closed_without_new_authority() -> None:
    text = DOC.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    assert "grants no authority for another command, retry, polling" in normalized
    assert "a missing result or an ambiguous result remains closed" in normalized
    assert "There is no fallback success, packet repair, automatic retry" in normalized
    assert "requires fresh evidence, a new LQ-2762 decision packet" in normalized
    assert "creates no parser, validator, command" in normalized
    assert "neither executes nor authorizes a staging reconciliation" in normalized


def test_runbook_links_outcome_validation_after_packet_completion() -> None:
    runbook = RUNBOOK.read_text(encoding="utf-8")
    normalized = " ".join(runbook.split())
    assert "lq-2765-staging-reconciliation-exercise-outcome-packet-validation.md" in runbook
    assert "Validate the completed outcome packet once" in normalized
    assert "Record only `valid`, `invalid` or `unverified`" in normalized
    assert "does not authorize another exercise" in normalized
