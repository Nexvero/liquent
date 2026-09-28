from pathlib import Path

import pytest

from liquent_platform.transport import (
    staging_research_index_promotion_reconciliation_process_outcome as outcome_module,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_process_outcome import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationProcessOutcome,
    StagingResearchIndexPromotionReconciliationProcessOutcomeUnavailable,
    observe_staging_research_index_promotion_reconciliation_process_outcome,
)
from tests.test_staging_research_index_promotion_attempt_journal import _receipt
from tests.test_staging_research_index_promotion_reconciliation import _unknown


def install(monkeypatch, value=None, error=None):
    calls = []

    def run(path):
        calls.append(path)
        if error is not None:
            raise error
        return value

    monkeypatch.setattr(
        outcome_module,
        "run_ready_staging_research_index_promotion_reconciliation_process",
        run,
    )
    return calls


def test_neutral_absence_becomes_idle_without_detail(monkeypatch) -> None:
    path = Path("/run/liquent/reconciliation.env")
    calls = install(monkeypatch, None)
    outcome = observe_staging_research_index_promotion_reconciliation_process_outcome(
        path
    )
    assert outcome is StagingResearchIndexPromotionReconciliationProcessOutcome.IDLE
    assert calls == [path]


def test_exact_receipt_becomes_reconciled_without_identity(monkeypatch) -> None:
    receipt = _receipt(_unknown().attempt.prepared)
    install(monkeypatch, receipt)
    outcome = observe_staging_research_index_promotion_reconciliation_process_outcome(
        Path("/run/liquent/reconciliation.env")
    )
    assert outcome is StagingResearchIndexPromotionReconciliationProcessOutcome.RECONCILED
    assert receipt.operation_id not in repr(outcome)


def test_technical_failure_is_detail_free(monkeypatch) -> None:
    install(monkeypatch, error=RuntimeError("provider detail"))
    with pytest.raises(
        StagingResearchIndexPromotionReconciliationProcessOutcomeUnavailable
    ) as caught:
        observe_staging_research_index_promotion_reconciliation_process_outcome(
            Path("/run/liquent/reconciliation.env")
        )
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert "provider detail" not in str(caught.value)


def test_unknown_result_fails_closed(monkeypatch) -> None:
    install(monkeypatch, object())
    with pytest.raises(StagingResearchIndexPromotionReconciliationProcessOutcomeUnavailable):
        observe_staging_research_index_promotion_reconciliation_process_outcome(
            Path("/run/liquent/reconciliation.env")
        )


def test_outcome_has_no_receipt_authority_or_retry_surface() -> None:
    for outcome in StagingResearchIndexPromotionReconciliationProcessOutcome:
        for forbidden in ("receipt", "operation_id", "authority", "retry"):
            assert not hasattr(outcome, forbidden)
