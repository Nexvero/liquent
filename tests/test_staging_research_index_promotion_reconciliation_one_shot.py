from pathlib import Path

import pytest

from liquent_platform.transport import (
    staging_research_index_promotion_reconciliation_one_shot as one_shot_module,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_one_shot import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationOneShotUnavailable,
    run_one_staging_research_index_promotion_reconciliation,
)
from tests.test_staging_research_index_promotion_attempt_journal import _receipt
from tests.test_staging_research_index_promotion_reconciliation import _unknown


class Runtime:
    def __init__(self, result=None, error=None, close_error=None):
        self.result = result
        self.error = error
        self.close_error = close_error
        self.executions = 0
        self.closes = 0

    def execute_one(self):
        self.executions += 1
        if self.error is not None:
            raise self.error
        return self.result

    def close(self):
        self.closes += 1
        if self.close_error is not None:
            raise self.close_error


def install(monkeypatch, runtime):
    calls = []

    def compose(path, engine):
        calls.append((path, engine))
        return runtime

    monkeypatch.setattr(
        one_shot_module,
        "compose_database_backed_staging_research_index_promotion_reconciliation_runtime",
        compose,
    )
    return calls


def test_one_shot_returns_exact_receipt_and_closes_once(monkeypatch) -> None:
    receipt = _receipt(_unknown().attempt.prepared)
    runtime = Runtime(receipt)
    calls = install(monkeypatch, runtime)
    path = Path("/run/liquent/provider.env")
    engine = object()
    assert run_one_staging_research_index_promotion_reconciliation(path, engine) is receipt
    assert calls == [(path, engine)]
    assert runtime.executions == 1 and runtime.closes == 1


def test_neutral_absence_is_returned_and_closed(monkeypatch) -> None:
    runtime = Runtime(None)
    install(monkeypatch, runtime)
    assert run_one_staging_research_index_promotion_reconciliation(
        Path("/run/liquent/provider.env"), object()
    ) is None
    assert runtime.executions == 1 and runtime.closes == 1


def test_execution_failure_is_detail_free_and_still_closes(monkeypatch) -> None:
    runtime = Runtime(error=RuntimeError("provider detail"))
    install(monkeypatch, runtime)
    with pytest.raises(
        StagingResearchIndexPromotionReconciliationOneShotUnavailable
    ) as caught:
        run_one_staging_research_index_promotion_reconciliation(
            Path("/run/liquent/provider.env"), object()
        )
    assert runtime.executions == 1 and runtime.closes == 1
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert "provider detail" not in str(caught.value)


def test_unknown_result_fails_closed_without_repeat(monkeypatch) -> None:
    runtime = Runtime(object())
    install(monkeypatch, runtime)
    with pytest.raises(StagingResearchIndexPromotionReconciliationOneShotUnavailable):
        run_one_staging_research_index_promotion_reconciliation(
            Path("/run/liquent/provider.env"), object()
        )
    assert runtime.executions == 1 and runtime.closes == 1


def test_one_shot_surface_has_no_loop_retry_or_trigger() -> None:
    source = Path(one_shot_module.__file__).read_text()
    for forbidden in ("while True", "for _ in", "sleep(", "retry", "schedule", "cron"):
        assert forbidden not in source
