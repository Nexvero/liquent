"""Explicit one-shot boundary for staging promotion reconciliation."""

from pathlib import Path

from sqlalchemy import Engine

from liquent_platform.application.staging_research_index_atomic_promotion import (
    StagingResearchIndexPromotionReceipt,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_database_composition import (  # noqa: E501
    compose_database_backed_staging_research_index_promotion_reconciliation_runtime,
)


class StagingResearchIndexPromotionReconciliationOneShotUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__(
            "staging_research_index_promotion_reconciliation_one_shot_unavailable"
        )


def run_one_staging_research_index_promotion_reconciliation(
    settings_path: Path,
    engine: Engine,
) -> StagingResearchIndexPromotionReceipt | None:
    """Compose, execute at most one operation, and always close the runtime."""

    runtime = None
    try:
        runtime = (
            compose_database_backed_staging_research_index_promotion_reconciliation_runtime(
                settings_path, engine
            )
        )
        result = runtime.execute_one()
        if result is not None and type(result) is not StagingResearchIndexPromotionReceipt:
            raise StagingResearchIndexPromotionReconciliationOneShotUnavailable
        return result
    except StagingResearchIndexPromotionReconciliationOneShotUnavailable as error:
        if error.__cause__ is None and error.__context__ is None:
            raise
    except Exception:
        pass
    finally:
        if runtime is not None:
            try:
                runtime.close()
            except Exception:
                pass
    raise StagingResearchIndexPromotionReconciliationOneShotUnavailable from None
