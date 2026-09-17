"""Select one untrusted staging promotion reconciliation candidate."""

import re
from typing import Protocol


_LIMIT = 100
_OPAQUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._~-]{0,255}\Z")


class StagingResearchIndexPromotionUnknownIndex(Protocol):
    def list_unknown_operation_ids(self) -> tuple[str, ...]: ...


class StagingResearchIndexPromotionCandidateSelectionUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__(
            "staging_research_index_promotion_candidate_selection_unavailable"
        )


def select_staging_research_index_promotion_reconciliation_candidate(
    unknowns: StagingResearchIndexPromotionUnknownIndex,
) -> str | None:
    """Return one validated identity without claiming or executing it."""

    try:
        operation_ids = unknowns.list_unknown_operation_ids()
        if type(operation_ids) is not tuple or len(operation_ids) > _LIMIT:
            raise StagingResearchIndexPromotionCandidateSelectionUnavailable
        if len(set(operation_ids)) != len(operation_ids):
            raise StagingResearchIndexPromotionCandidateSelectionUnavailable
        if tuple(sorted(operation_ids)) != operation_ids:
            raise StagingResearchIndexPromotionCandidateSelectionUnavailable
        if any(
            type(operation_id) is not str
            or _OPAQUE.fullmatch(operation_id) is None
            for operation_id in operation_ids
        ):
            raise StagingResearchIndexPromotionCandidateSelectionUnavailable
        return operation_ids[0] if operation_ids else None
    except StagingResearchIndexPromotionCandidateSelectionUnavailable as error:
        if error.__cause__ is None and error.__context__ is None:
            raise
    except Exception:
        pass
    raise StagingResearchIndexPromotionCandidateSelectionUnavailable from None
