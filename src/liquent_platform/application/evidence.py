"""JSON-safe projection of existing neutral research evidence."""

from __future__ import annotations

import math

from liquent.backtesting.reporting import BacktestExperimentSummary, summary_to_dict


def evidence_document(summary: BacktestExperimentSummary) -> dict[str, object]:
    """Return existing evidence with non-finite metrics represented as null."""

    document = summary_to_dict(summary)
    metrics = document.get("metrics")
    if isinstance(metrics, dict):
        document["metrics"] = {
            key: value
            if not isinstance(value, float) or math.isfinite(value)
            else None
            for key, value in metrics.items()
        }
    return document
