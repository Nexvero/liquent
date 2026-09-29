"""Read-only readiness audit for the staging reconciliation process."""

from enum import Enum
from pathlib import Path

from liquent_platform.application.health import Readiness
from liquent_platform.persistence.database import DatabaseReadinessProbe, build_engine
from liquent_platform.transport.staging_research_index_promotion_provider_settings_source import (  # noqa: E501
    load_staging_research_index_promotion_provider_settings,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_process_settings_source import (  # noqa: E501
    load_staging_research_index_promotion_reconciliation_process_settings,
)


class StagingResearchIndexPromotionReconciliationReadiness(Enum):
    READY = "ready"


class StagingResearchIndexPromotionReconciliationReadinessAuditUnavailable(
    Exception
):
    def __init__(self) -> None:
        super().__init__(
            "staging_research_index_promotion_reconciliation_readiness_audit_unavailable"
        )


def audit_staging_research_index_promotion_reconciliation_readiness(
    process_settings_path: Path,
) -> StagingResearchIndexPromotionReconciliationReadiness:
    """Validate installed settings and database readiness without reconciliation."""

    engine = None
    try:
        settings = (
            load_staging_research_index_promotion_reconciliation_process_settings(
                process_settings_path
            )
        )
        load_staging_research_index_promotion_provider_settings(
            settings.provider_settings_file
        )
        engine = build_engine(settings.database_url)
        readiness = DatabaseReadinessProbe(engine).check()
        if type(readiness) is not Readiness or not readiness.ready:
            raise StagingResearchIndexPromotionReconciliationReadinessAuditUnavailable
        return StagingResearchIndexPromotionReconciliationReadiness.READY
    except StagingResearchIndexPromotionReconciliationReadinessAuditUnavailable as error:
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
    raise StagingResearchIndexPromotionReconciliationReadinessAuditUnavailable from None
