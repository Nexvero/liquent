from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-2763-staging-reconciliation-exercise-decision-packet-validation.md"
RUNBOOK = ROOT / "operations/runbooks/staging-promotion.md"


def test_validation_is_manual_point_in_time_evidence_only() -> None:
    text = DOC.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    assert "manual validation boundary" in normalized
    assert "before one future staging reconciliation exercise" in normalized
    assert "does not turn the packet into a credential" in normalized
    assert "No packet value is copied into a ticket, command line, log" in normalized


def test_validation_is_ordered_complete_and_non_repairing() -> None:
    text = DOC.read_text(encoding="utf-8")
    headings = (
        "**Shape**",
        "**Tokens**",
        "**Window**",
        "**Current evidence**",
        "**Role separation**",
        "**Single use**",
    )
    positions = [text.index(heading) for heading in headings]
    assert positions == sorted(positions)
    assert "Stop at the first failed step" in text
    assert "Do not repair, infer, normalize or complete a\npacket" in text


def test_validation_has_fixed_data_minimizing_results() -> None:
    text = DOC.read_text(encoding="utf-8")
    for result in ("`valid`", "`rejected`", "`expired`", "`invalid`"):
        assert result in text
    assert "contains no field values, reason detail, path, endpoint" in text
    assert "`valid` is point-in-time evidence only" in text


def test_validation_fails_closed_and_is_single_use() -> None:
    text = DOC.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    assert "a missing result or an ambiguous result stops" in normalized
    assert "There is no fallback approval, packet repair, retry, polling" in normalized
    assert "A second attempt requires fresh evidence, a new LQ-2762 packet" in normalized
    assert "creates no parser, validator, command" in normalized
    assert "neither performs nor authorizes the real staging exercise" in normalized


def test_runbook_links_validation_without_granting_command_authority() -> None:
    runbook = RUNBOOK.read_text(encoding="utf-8")
    normalized = " ".join(runbook.split())
    assert "lq-2763-staging-reconciliation-exercise-decision-packet-validation.md" in runbook
    assert "Record only `valid`, `rejected`, `expired` or `invalid`" in runbook
    assert "A `valid` result is point-in-time evidence, not command authority" in normalized
