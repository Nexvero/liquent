"""Owned, manually triggered staging promotion reconciliation runtime."""

from pathlib import Path

from liquent_platform.application.staging_research_index_atomic_promotion import (
    StagingResearchIndexPromotionReceipt,
)
from liquent_platform.application.staging_research_index_promotion_reconciliation import (  # noqa: E501
    ReconciledStagingResearchIndexPromotionRecorder,
)
from liquent_platform.application.staging_research_index_promotion_reconciliation_candidate import (  # noqa: E501
    StagingResearchIndexPromotionUnknownIndex,
)
from liquent_platform.application.staging_research_index_promotion_reconciliation_execution import (  # noqa: E501
    execute_one_staging_research_index_promotion_reconciliation,
)
from liquent_platform.application.staging_research_index_promotion_reconciliation_operation import (  # noqa: E501
    StagingResearchIndexPromotionUnknownResolver,
)
from liquent_platform.transport.staging_research_index_promotion_provider_lifecycle import (  # noqa: E501
    StagingResearchIndexPromotionProviderLifecycle,
    compose_owned_staging_research_index_promotion_provider_lifecycle,
)


class StagingResearchIndexPromotionReconciliationRuntimeUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__(
            "staging_research_index_promotion_reconciliation_runtime_unavailable"
        )


class StagingResearchIndexPromotionReconciliationRuntime:
    __slots__ = ("_lifecycle", "_index", "_unknowns", "_recorder", "_closed")

    def __init__(
        self,
        lifecycle: StagingResearchIndexPromotionProviderLifecycle,
        index: StagingResearchIndexPromotionUnknownIndex,
        unknowns: StagingResearchIndexPromotionUnknownResolver,
        recorder: ReconciledStagingResearchIndexPromotionRecorder,
    ) -> None:
        if type(lifecycle) is not StagingResearchIndexPromotionProviderLifecycle:
            raise StagingResearchIndexPromotionReconciliationRuntimeUnavailable
        self._lifecycle = lifecycle
        self._index = index
        self._unknowns = unknowns
        self._recorder = recorder
        self._closed = False

    def __repr__(self) -> str:
        return "StagingResearchIndexPromotionReconciliationRuntime()"

    def execute_one(self) -> StagingResearchIndexPromotionReceipt | None:
        if self._closed:
            raise StagingResearchIndexPromotionReconciliationRuntimeUnavailable
        try:
            return execute_one_staging_research_index_promotion_reconciliation(
                self._index,
                self._unknowns,
                self._lifecycle.observer,
                self._recorder,
            )
        except Exception:
            pass
        raise StagingResearchIndexPromotionReconciliationRuntimeUnavailable from None

    def __enter__(self) -> "StagingResearchIndexPromotionReconciliationRuntime":
        if self._closed:
            raise StagingResearchIndexPromotionReconciliationRuntimeUnavailable
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            try:
                self._lifecycle.close()
            except Exception:
                raise StagingResearchIndexPromotionReconciliationRuntimeUnavailable from None


def compose_staging_research_index_promotion_reconciliation_runtime(
    settings_path: Path,
    index: StagingResearchIndexPromotionUnknownIndex,
    unknowns: StagingResearchIndexPromotionUnknownResolver,
    recorder: ReconciledStagingResearchIndexPromotionRecorder,
) -> StagingResearchIndexPromotionReconciliationRuntime:
    lifecycle = None
    try:
        lifecycle = compose_owned_staging_research_index_promotion_provider_lifecycle(
            settings_path
        )
        return StagingResearchIndexPromotionReconciliationRuntime(
            lifecycle, index, unknowns, recorder
        )
    except Exception:
        if lifecycle is not None:
            try:
                lifecycle.close()
            except Exception:
                pass
    raise StagingResearchIndexPromotionReconciliationRuntimeUnavailable from None
