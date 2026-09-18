"""Readiness-gated one-shot staging promotion reconciliation process."""

from pathlib import Path

from liquent_platform.application.health import Readiness
from liquent_platform.application.staging_research_index_atomic_promotion import (
    StagingResearchIndexPromotionReceipt,
)
from liquent_platform.persistence.database import DatabaseReadinessProbe, build_engine
from liquent_platform.transport.staging_research_index_promotion_reconciliation_one_shot import (  # noqa: E501
    run_one_staging_research_index_promotion_reconciliation,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_process_settings_source import (  # noqa: E501
    load_staging_research_index_promotion_reconciliation_process_settings,
)


class StagingResearchIndexPromotionReconciliationReadyProcessUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__(
            "staging_research_index_promotion_reconciliation_ready_process_unavailable"
        )


def run_ready_staging_research_index_promotion_reconciliation_process(
    process_settings_path: Path,
) -> StagingResearchIndexPromotionReceipt | None:
    """Execute once only after the existing database readiness gate passes."""

    engine = None
    try:
        settings = (
            load_staging_research_index_promotion_reconciliation_process_settings(
                process_settings_path
            )
        )
        engine = build_engine(settings.database_url)
        readiness = DatabaseReadinessProbe(engine).check()
        if type(readiness) is not Readiness or not readiness.ready:
            raise StagingResearchIndexPromotionReconciliationReadyProcessUnavailable
        result = run_one_staging_research_index_promotion_reconciliation(
            settings.provider_settings_file, engine
        )
        if result is not None and type(result) is not StagingResearchIndexPromotionReceipt:
            raise StagingResearchIndexPromotionReconciliationReadyProcessUnavailable
        return result
    except StagingResearchIndexPromotionReconciliationReadyProcessUnavailable as error:
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
    raise StagingResearchIndexPromotionReconciliationReadyProcessUnavailable from None
