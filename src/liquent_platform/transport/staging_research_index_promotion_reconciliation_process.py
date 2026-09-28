"""Owned one-shot process composition for staging promotion reconciliation."""

from pathlib import Path

from liquent_platform.application.staging_research_index_atomic_promotion import (
    StagingResearchIndexPromotionReceipt,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.transport.staging_research_index_promotion_reconciliation_one_shot import (  # noqa: E501
    run_one_staging_research_index_promotion_reconciliation,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_process_settings_source import (  # noqa: E501
    load_staging_research_index_promotion_reconciliation_process_settings,
)


class StagingResearchIndexPromotionReconciliationProcessUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__(
            "staging_research_index_promotion_reconciliation_process_unavailable"
        )


def run_staging_research_index_promotion_reconciliation_process(
    process_settings_path: Path,
) -> StagingResearchIndexPromotionReceipt | None:
    """Load, execute once, and always dispose the process-owned engine."""

    engine = None
    try:
        settings = (
            load_staging_research_index_promotion_reconciliation_process_settings(
                process_settings_path
            )
        )
        engine = build_engine(settings.database_url)
        result = run_one_staging_research_index_promotion_reconciliation(
            settings.provider_settings_file, engine
        )
        if result is not None and type(result) is not StagingResearchIndexPromotionReceipt:
            raise StagingResearchIndexPromotionReconciliationProcessUnavailable
        return result
    except StagingResearchIndexPromotionReconciliationProcessUnavailable as error:
        if error.__cause__ is None and error.__context__ is None:
            raise
    except Exception:
        pass
    finally:
        if engine is not None:
            try:
                engine.dispose()
            except Exception:
                pass
    raise StagingResearchIndexPromotionReconciliationProcessUnavailable from None
