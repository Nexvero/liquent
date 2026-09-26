import pytest

from liquent_platform.application.staging_research_index_promotion_reconciliation_candidate import (  # noqa: E501
    StagingResearchIndexPromotionCandidateSelectionUnavailable,
    select_staging_research_index_promotion_reconciliation_candidate,
)


class Unknowns:
    def __init__(self, operation_ids):
        self.operation_ids = operation_ids
        self.calls = 0

    def list_unknown_operation_ids(self):
        self.calls += 1
        return self.operation_ids


def test_first_deterministic_candidate_is_selected_once() -> None:
    unknowns = Unknowns(("promotion-2716-a", "promotion-2716-b"))
    assert (
        select_staging_research_index_promotion_reconciliation_candidate(unknowns)
        == "promotion-2716-a"
    )
    assert unknowns.calls == 1


def test_empty_index_is_neutral() -> None:
    unknowns = Unknowns(())
    assert (
        select_staging_research_index_promotion_reconciliation_candidate(unknowns)
        is None
    )
    assert unknowns.calls == 1


@pytest.mark.parametrize(
    "result",
    [
        ["promotion-2716"],
        ("promotion-b", "promotion-a"),
        ("promotion-a", "promotion-a"),
        ("not valid",),
        tuple(f"promotion-{number:03d}" for number in range(101)),
    ],
)
def test_malformed_index_results_fail_closed(result) -> None:
    with pytest.raises(StagingResearchIndexPromotionCandidateSelectionUnavailable):
        select_staging_research_index_promotion_reconciliation_candidate(
            Unknowns(result)
        )


def test_index_failure_is_detail_free() -> None:
    class Broken:
        def list_unknown_operation_ids(self):
            raise RuntimeError("database detail")

    with pytest.raises(
        StagingResearchIndexPromotionCandidateSelectionUnavailable
    ) as caught:
        select_staging_research_index_promotion_reconciliation_candidate(Broken())
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert "database detail" not in str(caught.value)


def test_selection_exposes_no_claim_or_execution_capability() -> None:
    unknowns = Unknowns(("promotion-2716",))
    select_staging_research_index_promotion_reconciliation_candidate(unknowns)
    assert not hasattr(unknowns, "claim")
    assert not hasattr(unknowns, "observe")
    assert not hasattr(unknowns, "retry")
