"""Read-only candidate audit for the staging reconciliation process."""

from enum import Enum
from pathlib import Path

from liquent_platform.application.health import Readiness
from liquent_platform.application.staging_research_index_promotion_reconciliation_candidate import (  # noqa: E501
    select_staging_research_index_promotion_reconciliation_candidate,
)
from liquent_platform.persistence.database import DatabaseReadinessProbe, build_engine
from liquent_platform.persistence.staging_research_index_promotion_unknown_index import (  # noqa: E501
    DatabaseStagingResearchIndexPromotionUnknownIndex,
)
from liquent_platform.transport.staging_research_index_promotion_provider_settings_source import (  # noqa: E501
    load_staging_research_index_promotion_provider_settings,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_process_settings_source import (  # noqa: E501
    load_staging_research_index_promotion_reconciliation_process_settings,
)


class StagingResearchIndexPromotionReconciliationCandidateAudit(Enum):
    PENDING = "pending"
    IDLE = "idle"


class StagingResearchIndexPromotionReconciliationCandidateAuditUnavailable(
    Exception
):
    def __init__(self) -> None:
        super().__init__(
            "staging_research_index_promotion_reconciliation_candidate_audit_unavailable"
        )


def audit_staging_research_index_promotion_reconciliation_candidate(
    process_settings_path: Path,
) -> StagingResearchIndexPromotionReconciliationCandidateAudit:
    """Report only whether one eligible unknown-effect candidate exists."""

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
            raise StagingResearchIndexPromotionReconciliationCandidateAuditUnavailable
        candidate = (
            select_staging_research_index_promotion_reconciliation_candidate(
                DatabaseStagingResearchIndexPromotionUnknownIndex(engine)
            )
        )
        if candidate is None:
            return StagingResearchIndexPromotionReconciliationCandidateAudit.IDLE
        return StagingResearchIndexPromotionReconciliationCandidateAudit.PENDING
    except StagingResearchIndexPromotionReconciliationCandidateAuditUnavailable as error:
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
    raise StagingResearchIndexPromotionReconciliationCandidateAuditUnavailable from None
