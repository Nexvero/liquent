from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-2764-staging-reconciliation-exercise-outcome-packet.md"
RUNBOOK = ROOT / "operations/runbooks/staging-promotion.md"


def test_outcome_packet_is_completion_evidence_without_new_authority() -> None:
    text = DOC.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    assert "minimal completion record for one bounded staging" in normalized
    assert "fixed command outcomes" in normalized
    assert "not a credential, retry request, promotion decision" in normalized
    assert "including when it stops before the reconciliation command" in normalized


def test_outcome_packet_has_closed_fixed_shape() -> None:
    text = DOC.read_text(encoding="utf-8")
    for field in (
        "decision_validation: valid",
        "settings_installation: installed|present|unavailable|invalid_invocation|not_run",
        "readiness_audit: ready|unavailable|invalid_invocation|not_run",
        "candidate_audit: pending|idle|unavailable|invalid_invocation|not_run",
        "reconciliation: reconciled|idle|unavailable|invalid_invocation|not_run",
        "final_candidate_state: reconciled|present|unverified",
        "exercise_result: completed|stopped|unverified",
        "window_closed_utc: YYYY-MM-DDTHH:MM:SSZ",
    ):
        assert field in text
    assert "must never be used to hide an invoked command's result" in text


def test_outcome_requires_independent_final_state_and_fails_closed() -> None:
    text = DOC.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    assert "independently inspect the system of record" in normalized
    assert "`completed` is valid only when reconciliation reported `reconciled`" in normalized
    assert "Any mismatch, missing fact or unavailable final inspection is `unverified`" in normalized
    assert "Any later pass requires fresh evidence, a new LQ-2762 decision packet" in normalized


def test_outcome_packet_excludes_sensitive_and_executable_material() -> None:
    text = DOC.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    assert "contains no settings path or value, provider endpoint, database URL" in normalized
    assert "cannot authorize another command, retry, polling" in normalized
    assert "creates no command, parser, writer, database record" in normalized
    assert "does not execute the staging exercise or mutate durable state" in normalized


def test_runbook_links_outcome_packet_after_the_bounded_exercise() -> None:
    runbook = RUNBOOK.read_text(encoding="utf-8")
    normalized = " ".join(runbook.split())
    assert "lq-2764-staging-reconciliation-exercise-outcome-packet.md" in runbook
    assert "Record the fixed result of every invoked command" in normalized
    assert "Verify the final candidate state independently through the system of record" in normalized
    assert "The outcome packet grants no authority for another pass" in normalized
