"""Database-backed composition for the controlled reconciliation runtime."""

from pathlib import Path

from sqlalchemy import Engine

from liquent_platform.persistence.staging_research_index_promotion_attempt_journal import (  # noqa: E501
    DatabaseStagingResearchIndexPromotionAttemptJournal,
)
from liquent_platform.persistence.staging_research_index_promotion_unknown_index import (  # noqa: E501
    DatabaseStagingResearchIndexPromotionUnknownIndex,
)
from liquent_platform.persistence.staging_research_index_promotion_unknown_reader import (  # noqa: E501
    DatabaseStagingResearchIndexPromotionUnknownReader,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_runtime import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationRuntime,
    compose_staging_research_index_promotion_reconciliation_runtime,
)


class StagingResearchIndexPromotionReconciliationDatabaseCompositionUnavailable(
    Exception
):
    def __init__(self) -> None:
        super().__init__(
            "staging_research_index_promotion_reconciliation_database_composition_unavailable"
        )


def compose_database_backed_staging_research_index_promotion_reconciliation_runtime(
    settings_path: Path,
    engine: Engine,
) -> StagingResearchIndexPromotionReconciliationRuntime:
    """Bind one existing engine to all three durable reconciliation ports."""

    try:
        if not isinstance(engine, Engine):
            raise (
                StagingResearchIndexPromotionReconciliationDatabaseCompositionUnavailable
            )
        index = DatabaseStagingResearchIndexPromotionUnknownIndex(engine)
        unknowns = DatabaseStagingResearchIndexPromotionUnknownReader(engine)
        recorder = DatabaseStagingResearchIndexPromotionAttemptJournal(engine)
        return compose_staging_research_index_promotion_reconciliation_runtime(
            settings_path, index, unknowns, recorder
        )
    except StagingResearchIndexPromotionReconciliationDatabaseCompositionUnavailable as error:
        if error.__cause__ is None and error.__context__ is None:
            raise
    except Exception:
        pass
    raise StagingResearchIndexPromotionReconciliationDatabaseCompositionUnavailable from None
