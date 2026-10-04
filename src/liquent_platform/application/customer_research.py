"""Bridge the existing three-variant pilot to authenticated persistent research."""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol

from liquent.backtesting.reporting import BacktestExperimentSummary
from liquent.research_pilot.contracts import MODEL_LIMITS
from liquent.research_pilot.customer_report import pilot_to_dict
from liquent.research_pilot.execution import canonical_json, execute_pilot, fingerprint
from liquent_platform.application.experiment import ExperimentSnapshot

PILOT_STRATEGY_VERSION = "research-pilot-v1"
PILOT_RESULT_PARAMETER = "pilot_result_json"


def customer_input_binding(raw: bytes, configuration: dict) -> str:
    """Bind unchanged dataset bytes to the complete explicit configuration."""
    import hashlib

    return fingerprint({
        "dataset_fingerprint": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "configuration": configuration,
    })


class PilotBacktestExecution:
    """Execute only the private, immutable upload accepted by existing jobs."""

    def __init__(self, raw: bytes, configuration: dict, experiment_id: str) -> None:
        self._raw = raw
        self._configuration = configuration
        self._experiment_id = experiment_id

    def run_summary(self, *, title: str) -> BacktestExperimentSummary:
        with TemporaryDirectory(prefix="liquent-research-job-") as directory:
            root = Path(directory)
            os.chmod(root, 0o700)
            path = root / "dataset.csv"
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(self._raw)
            result = execute_pilot(path, self._configuration)
        payload = pilot_to_dict(result)
        # This is a transport carrier, NOT a combined performance summary.
        # evidence_document exposes aggregate performance as unavailable, and
        # preserves failed/no-signal variants and all actual variant metrics.
        return BacktestExperimentSummary(
            experiment_id=self._experiment_id, title=title,
            strategy_name=PILOT_STRATEGY_VERSION,
            starting_equity=0.0, ending_equity=0.0, number_of_trades=0,
            approved_signals=0, rejected_signals=0, metrics={},
            parameters={PILOT_RESULT_PARAMETER: canonical_json(payload)},
            risk_notes=MODEL_LIMITS,
            safety_flags={"live_execution": False, "network_calls": False,
                          "paper_trading": False},
        )


class CustomerResearchStore(Protocol):
    """Application-owned port; adapters are injected at composition boundaries."""

    def bind_request(self, owner: str, workspace: str, raw: bytes,
                     configuration: dict, expected_binding: str,
                     data_rights: bool, execution_approved: bool) -> ExperimentSnapshot: ...

    def save_feedback(self, owner: str, workspace: str, value: dict,
                      synthetic: bool) -> None: ...

    def resolve(self, snapshot: ExperimentSnapshot) -> PilotBacktestExecution: ...
