"""Closed application evaluation of staging Research-index observations."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import re
from urllib.parse import urlsplit


class StagingResearchIndexCheck(str, Enum):
    ANONYMOUS_CLOSED = "anonymous_closed"
    AUTHORIZED_EMPTY = "authorized_empty"
    AUTHORIZED_VISIBLE = "authorized_visible"
    MINIMUM_FIELDS = "minimum_fields"
    SECURITY_HEADERS = "security_headers"
    QUERY_REJECTED = "query_rejected"
    REVOCATION_FRESH = "revocation_fresh"
    UNAVAILABLE_DETAIL_FREE = "unavailable_detail_free"


class StagingResearchIndexCheckOutcome(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


class StagingResearchIndexAcceptanceOutcome(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class StagingResearchIndexAcceptanceRun:
    candidate_digest: str
    staging_origin: str
    observed_at: datetime

    def __post_init__(self) -> None:
        if re.fullmatch(r"sha256:[0-9a-f]{64}", self.candidate_digest) is None:
            raise ValueError("candidate digest must be canonical sha256")
        parsed = urlsplit(self.staging_origin)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("staging origin must be an exact https origin")
        if (
            type(self.observed_at) is not datetime
            or self.observed_at.tzinfo is None
            or self.observed_at.utcoffset() != timedelta(0)
        ):
            raise ValueError("acceptance observation time must be UTC")


@dataclass(frozen=True, slots=True)
class StagingResearchIndexObservation:
    check: StagingResearchIndexCheck
    outcome: StagingResearchIndexCheckOutcome


@dataclass(frozen=True, slots=True)
class StagingResearchIndexAcceptanceResult:
    run: StagingResearchIndexAcceptanceRun
    outcome: StagingResearchIndexAcceptanceOutcome


def evaluate_staging_research_index_acceptance(
    run: StagingResearchIndexAcceptanceRun,
    observations: tuple[StagingResearchIndexObservation, ...],
) -> StagingResearchIndexAcceptanceResult:
    """Evaluate one complete run without network, persistence, or mutation."""

    if any(
        type(observation) is not StagingResearchIndexObservation
        or type(observation.check) is not StagingResearchIndexCheck
        or type(observation.outcome) is not StagingResearchIndexCheckOutcome
        for observation in observations
    ):
        return StagingResearchIndexAcceptanceResult(
            run, StagingResearchIndexAcceptanceOutcome.REJECTED
        )

    checks = tuple(observation.check for observation in observations)
    required = frozenset(StagingResearchIndexCheck)
    if len(checks) != len(required) or frozenset(checks) != required:
        outcome = StagingResearchIndexAcceptanceOutcome.REJECTED
    elif any(
        observation.outcome is StagingResearchIndexCheckOutcome.UNAVAILABLE
        for observation in observations
    ):
        outcome = StagingResearchIndexAcceptanceOutcome.UNAVAILABLE
    elif any(
        observation.outcome is StagingResearchIndexCheckOutcome.FAILED
        for observation in observations
    ):
        outcome = StagingResearchIndexAcceptanceOutcome.REJECTED
    else:
        outcome = StagingResearchIndexAcceptanceOutcome.ACCEPTED
    return StagingResearchIndexAcceptanceResult(run, outcome)
