import pytest

from liquent_platform.application.staging_research_index_promotion_reconciliation import (
    ObservedCommittedStagingResearchIndexPromotion,
)
from liquent_platform.application.staging_research_index_promotion_reconciliation_operation import (
    StagingResearchIndexPromotionReconciliationOperationUnavailable,
    reconcile_staging_research_index_promotion_operation,
)
from tests.test_staging_research_index_promotion_attempt_journal import NOW, _receipt
from tests.test_staging_research_index_promotion_reconciliation import (
    Outcomes,
    Recorder,
    _unknown,
)


class Unknowns:
    def __init__(self, unknown):
        self.unknown = unknown
        self.calls = []

    def resolve_unknown(self, operation_id):
        self.calls.append(operation_id)
        return self.unknown


def test_one_exact_unknown_operation_is_observed_and_recorded() -> None:
    unknown = _unknown()
    operation = unknown.attempt.prepared.operation_id
    receipt = _receipt(unknown.attempt.prepared)
    unknowns = Unknowns(unknown)
    outcomes = Outcomes(ObservedCommittedStagingResearchIndexPromotion(receipt, NOW))
    recorder = Recorder()
    assert reconcile_staging_research_index_promotion_operation(
        operation, unknowns, outcomes, recorder
    ) is receipt
    assert unknowns.calls == [operation]
    assert outcomes.calls == [unknown]
    assert recorder.calls == [(unknown, receipt, NOW)]


def test_absent_or_completed_operation_is_neutral_without_observation() -> None:
    outcomes = Outcomes(None)
    recorder = Recorder()
    assert reconcile_staging_research_index_promotion_operation(
        "promotion-2714", Unknowns(None), outcomes, recorder
    ) is None
    assert outcomes.calls == []
    assert recorder.calls == []


def test_unknown_without_committed_observation_remains_neutral() -> None:
    unknown = _unknown()
    outcomes = Outcomes(None)
    recorder = Recorder()
    assert reconcile_staging_research_index_promotion_operation(
        unknown.attempt.prepared.operation_id,
        Unknowns(unknown),
        outcomes,
        recorder,
    ) is None
    assert outcomes.calls == [unknown]
    assert recorder.calls == []


def test_substituted_unknown_and_reader_failure_are_detail_free() -> None:
    unknown = _unknown()
    with pytest.raises(
        StagingResearchIndexPromotionReconciliationOperationUnavailable
    ):
        reconcile_staging_research_index_promotion_operation(
            "different-operation", Unknowns(unknown), Outcomes(None), Recorder()
        )

    class Broken:
        def resolve_unknown(self, _operation):
            raise RuntimeError("database detail")

    with pytest.raises(
        StagingResearchIndexPromotionReconciliationOperationUnavailable
    ) as caught:
        reconcile_staging_research_index_promotion_operation(
            "promotion-2714", Broken(), Outcomes(None), Recorder()
        )
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert "database detail" not in str(caught.value)


def test_malformed_operation_never_reaches_reader() -> None:
    unknowns = Unknowns(None)
    with pytest.raises(
        StagingResearchIndexPromotionReconciliationOperationUnavailable
    ):
        reconcile_staging_research_index_promotion_operation(
            "not valid", unknowns, Outcomes(None), Recorder()
        )
    assert unknowns.calls == []
