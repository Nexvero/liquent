from dataclasses import replace

import pytest

from liquent_platform.adapters.staging_research_index_promotion_outcome import (
    StagingResearchIndexPromotionOutcomeAdapterUnavailable,
    TrustedCommittedStagingResearchIndexPromotionStatus,
    TrustedStagingResearchIndexPromotionOutcomeAdapter,
)
from tests.test_staging_research_index_promotion_attempt_journal import NOW
from tests.test_staging_research_index_promotion_reconciliation import _unknown


class Gateway:
    def __init__(self, status):
        self.status = status
        self.calls = []

    def read_committed(self, operation_id):
        self.calls.append(operation_id)
        return self.status


def _status(unknown):
    prepared = unknown.attempt.prepared
    return TrustedCommittedStagingResearchIndexPromotionStatus(
        prepared.operation_id,
        prepared.command.actor.user_id,
        prepared.command.evidence_digest,
        prepared.authority.candidate_digest,
        prepared.authority.staging_origin,
        prepared.authority.target_environment,
        NOW,
    )


def test_exact_committed_status_becomes_trusted_observation() -> None:
    unknown = _unknown()
    gateway = Gateway(_status(unknown))
    adapter = TrustedStagingResearchIndexPromotionOutcomeAdapter(gateway)
    observation = adapter.observe_committed(unknown)
    assert observation is not None
    assert observation.receipt.operation_id == unknown.attempt.prepared.operation_id
    assert observation.observed_at == NOW
    assert gateway.calls == [unknown.attempt.prepared.operation_id]
    assert repr(adapter) == "TrustedStagingResearchIndexPromotionOutcomeAdapter()"


def test_absent_commit_is_neutral() -> None:
    unknown = _unknown()
    gateway = Gateway(None)
    assert TrustedStagingResearchIndexPromotionOutcomeAdapter(
        gateway
    ).observe_committed(unknown) is None
    assert gateway.calls == [unknown.attempt.prepared.operation_id]


@pytest.mark.parametrize(
    "field,value",
    [
        ("operation_id", "substituted"),
        ("target_environment", "production-other"),
        ("staging_origin", "https://substituted.invalid"),
    ],
)
def test_substituted_status_fails_closed(field, value) -> None:
    unknown = _unknown()
    status = replace(_status(unknown), **{field: value})
    with pytest.raises(StagingResearchIndexPromotionOutcomeAdapterUnavailable):
        TrustedStagingResearchIndexPromotionOutcomeAdapter(
            Gateway(status)
        ).observe_committed(unknown)


def test_gateway_failure_is_detail_free_and_grants_no_retry() -> None:
    class Broken:
        def read_committed(self, _operation_id):
            raise RuntimeError("provider detail")

    adapter = TrustedStagingResearchIndexPromotionOutcomeAdapter(Broken())
    with pytest.raises(StagingResearchIndexPromotionOutcomeAdapterUnavailable) as caught:
        adapter.observe_committed(_unknown())
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert "provider detail" not in str(caught.value)
    assert not hasattr(adapter, "promote")
    assert not hasattr(adapter, "retry")
