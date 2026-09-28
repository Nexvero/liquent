"""Closed read-only classifications for child-owned execution evidence."""

from dataclasses import dataclass
from enum import Enum


class ManifestHandoffSupervisorExecutionReconciliationStatus(str, Enum):
    WAITING_FOR_CHILD_CONSUMPTION = "waiting_for_child_consumption"
    CHILD_CAPABILITY_IN_FLIGHT = "child_capability_in_flight"
    AMBIGUOUS_AFTER_CONSUMPTION = "ambiguous_after_consumption"
    WAITING_FOR_ENGINE_TERMINAL = "waiting_for_engine_terminal"
    TERMINAL_EVIDENCE_READY = "terminal_evidence_ready"
    BLOCKED_DIVERGENCE = "blocked_divergence"


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorExecutionReconciliation:
    status: ManifestHandoffSupervisorExecutionReconciliationStatus
    may_start_child: bool = False
    may_publish_release: bool = False
    may_execute_capability: bool = False

    def __post_init__(self) -> None:
        if (type(self.status) is not ManifestHandoffSupervisorExecutionReconciliationStatus
                or self.may_start_child is not False
                or self.may_publish_release is not False
                or self.may_execute_capability is not False):
            raise ValueError("manifest handoff supervisor reconciliation is invalid")
