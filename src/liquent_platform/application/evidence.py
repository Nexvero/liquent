"""JSON-safe projection of existing neutral research evidence."""

from __future__ import annotations

import math
import json

from liquent.backtesting.reporting import BacktestExperimentSummary, summary_to_dict


def evidence_document(summary: BacktestExperimentSummary) -> dict[str, object]:
    """Return existing evidence with non-finite metrics represented as null."""

    document = summary_to_dict(summary)
    from liquent_platform.application.customer_research import (
        PILOT_RESULT_PARAMETER, PILOT_STRATEGY_VERSION,
    )
    from liquent.research_pilot.contracts import RESULT_SCHEMA

    if summary.strategy_name == PILOT_STRATEGY_VERSION:
        payload = json.loads(summary.parameters[PILOT_RESULT_PARAMETER])
        if (not isinstance(payload, dict) or payload.get("schema") != RESULT_SCHEMA
                or not isinstance(payload.get("variants"), list) or len(payload["variants"]) != 3):
            raise ValueError("Invalid three-variant research evidence")
        document["pilot_result"] = payload
        document["parameters"] = {"strategy": PILOT_STRATEGY_VERSION}
        document["aggregate_performance_available"] = False
        for key in ("starting_equity", "ending_equity", "number_of_trades",
                    "approved_signals", "rejected_signals"):
            document[key] = None
        return document
    metrics = document.get("metrics")
    if isinstance(metrics, dict):
        document["metrics"] = {
            key: value
            if not isinstance(value, float) or math.isfinite(value)
            else None
            for key, value in metrics.items()
        }
    return document
