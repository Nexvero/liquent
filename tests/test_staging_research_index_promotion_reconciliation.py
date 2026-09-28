from datetime import datetime, timezone

import pytest

from liquent_platform.application.staging_research_index_promotion_attempt import (
    UnknownStagingResearchIndexPromotionEffect,
    WriteStartedStagingResearchIndexPromotionAttempt,
)
from liquent_platform.application.staging_research_index_promotion_reconciliation import (
    ObservedCommittedStagingResearchIndexPromotion,
    StagingResearchIndexPromotionReconciliationUnavailable,
    reconcile_unknown_staging_research_index_promotion,
)
from tests.test_staging_research_index_promotion_attempt_journal import (
    NOW,
    _attempt,
    _receipt,
)


def _unknown():
    return UnknownStagingResearchIndexPromotionEffect(
        WriteStartedStagingResearchIndexPromotionAttempt(_attempt())
    )


class Outcomes:
    def __init__(self, observation):
        self.observation = observation
        self.calls = []

    def observe_committed(self, unknown):
        self.calls.append(unknown)
        return self.observation


class Recorder:
    def __init__(self):
        self.calls = []

    def record_reconciled_committed(self, unknown, receipt, *, observed_at):
        self.calls.append((unknown, receipt, observed_at))
        return receipt


def test_exact_trusted_observation_is_persisted() -> None:
    unknown = _unknown()
    receipt = _receipt(unknown.attempt.prepared)
    observation = ObservedCommittedStagingResearchIndexPromotion(receipt, NOW)
    outcomes = Outcomes(observation)
    recorder = Recorder()
    assert reconcile_unknown_staging_research_index_promotion(
        unknown, outcomes, recorder
    ) is receipt
    assert outcomes.calls == [unknown]
    assert recorder.calls == [(unknown, receipt, NOW)]
    assert repr(observation) == "ObservedCommittedStagingResearchIndexPromotion()"
    assert receipt.operation_id not in repr(observation)


def test_absent_committed_observation_is_neutral_and_does_not_write() -> None:
    unknown = _unknown()
    recorder = Recorder()
    assert reconcile_unknown_staging_research_index_promotion(
        unknown, Outcomes(None), recorder
    ) is None
    assert recorder.calls == []


def test_substituted_observation_fails_closed_without_write() -> None:
    unknown = _unknown()
    substituted = _receipt(unknown.attempt.prepared, "different-operation")
    recorder = Recorder()
    with pytest.raises(StagingResearchIndexPromotionReconciliationUnavailable):
        reconcile_unknown_staging_research_index_promotion(
            unknown,
            Outcomes(ObservedCommittedStagingResearchIndexPromotion(substituted, NOW)),
            recorder,
        )
    assert recorder.calls == []


def test_observer_and_recorder_failures_are_detail_free() -> None:
    unknown = _unknown()

    class BrokenOutcomes:
        def observe_committed(self, _unknown):
            raise RuntimeError("provider detail")

    with pytest.raises(StagingResearchIndexPromotionReconciliationUnavailable) as caught:
        reconcile_unknown_staging_research_index_promotion(
            unknown, BrokenOutcomes(), Recorder()
        )
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert "provider detail" not in str(caught.value)

    class BrokenRecorder:
        def record_reconciled_committed(self, *_args, **_kwargs):
            raise RuntimeError("database detail")

    receipt = _receipt(unknown.attempt.prepared)
    with pytest.raises(StagingResearchIndexPromotionReconciliationUnavailable) as caught:
        reconcile_unknown_staging_research_index_promotion(
            unknown,
            Outcomes(ObservedCommittedStagingResearchIndexPromotion(receipt, NOW)),
            BrokenRecorder(),
        )
    assert "database detail" not in str(caught.value)


def test_observation_requires_aware_time_and_grants_no_retry() -> None:
    receipt = _receipt(_unknown().attempt.prepared)
    with pytest.raises(ValueError):
        ObservedCommittedStagingResearchIndexPromotion(
            receipt, datetime(2026, 9, 16)
        )
    observation = ObservedCommittedStagingResearchIndexPromotion(
        receipt, datetime(2026, 9, 16, tzinfo=timezone.utc)
    )
    assert not hasattr(observation, "retry")
    assert not hasattr(observation, "authority")
