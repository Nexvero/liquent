import pytest

from liquent_platform.application.staging_research_index_promotion_reconciliation import (
    ObservedCommittedStagingResearchIndexPromotion,
)
from liquent_platform.application.staging_research_index_promotion_reconciliation_execution import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationExecutionUnavailable,
    execute_one_staging_research_index_promotion_reconciliation,
)
from tests.test_staging_research_index_promotion_attempt_journal import NOW, _receipt
from tests.test_staging_research_index_promotion_reconciliation import (
    Outcomes,
    Recorder,
    _unknown,
)
from tests.test_staging_research_index_promotion_reconciliation_candidate import (
    Unknowns as Index,
)
from tests.test_staging_research_index_promotion_reconciliation_operation import (
    Unknowns,
)


def test_one_selected_operation_is_reconciled() -> None:
    unknown = _unknown()
    operation_id = unknown.attempt.prepared.operation_id
    receipt = _receipt(unknown.attempt.prepared)
    index = Index((operation_id, "promotion-z"))
    unknowns = Unknowns(unknown)
    outcomes = Outcomes(ObservedCommittedStagingResearchIndexPromotion(receipt, NOW))
    recorder = Recorder()
    assert execute_one_staging_research_index_promotion_reconciliation(
        index, unknowns, outcomes, recorder
    ) is receipt
    assert index.calls == 1
    assert unknowns.calls == [operation_id]
    assert outcomes.calls == [unknown]
    assert recorder.calls == [(unknown, receipt, NOW)]


def test_empty_selection_is_neutral_without_loading_or_observing() -> None:
    index = Index(())
    unknowns = Unknowns(None)
    outcomes = Outcomes(None)
    recorder = Recorder()
    assert execute_one_staging_research_index_promotion_reconciliation(
        index, unknowns, outcomes, recorder
    ) is None
    assert unknowns.calls == []
    assert outcomes.calls == []
    assert recorder.calls == []


def test_absent_commit_observation_is_neutral_without_recording() -> None:
    unknown = _unknown()
    operation_id = unknown.attempt.prepared.operation_id
    outcomes = Outcomes(None)
    recorder = Recorder()
    assert execute_one_staging_research_index_promotion_reconciliation(
        Index((operation_id,)), Unknowns(unknown), outcomes, recorder
    ) is None
    assert outcomes.calls == [unknown]
    assert recorder.calls == []


def test_selection_or_operation_failure_is_detail_free() -> None:
    with pytest.raises(
        StagingResearchIndexPromotionReconciliationExecutionUnavailable
    ) as malformed:
        execute_one_staging_research_index_promotion_reconciliation(
            Index(("not valid",)), Unknowns(None), Outcomes(None), Recorder()
        )
    assert malformed.value.__cause__ is None
    assert malformed.value.__context__ is None

    class Broken:
        def resolve_unknown(self, _operation_id):
            raise RuntimeError("database detail")

    with pytest.raises(
        StagingResearchIndexPromotionReconciliationExecutionUnavailable
    ) as broken:
        execute_one_staging_research_index_promotion_reconciliation(
            Index(("promotion-2717",)), Broken(), Outcomes(None), Recorder()
        )
    assert broken.value.__cause__ is None and broken.value.__context__ is None
    assert "database detail" not in str(broken.value)


def test_execution_has_no_loop_claim_or_retry_surface() -> None:
    unknown = _unknown()
    first = unknown.attempt.prepared.operation_id
    unknowns = Unknowns(unknown)
    execute_one_staging_research_index_promotion_reconciliation(
        Index((first, "promotion-z")), unknowns, Outcomes(None), Recorder()
    )
    assert unknowns.calls == [first]
    assert not hasattr(unknowns, "claim")
    assert not hasattr(unknowns, "retry")
