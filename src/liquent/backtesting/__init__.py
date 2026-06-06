"""Backtesting-Framework für Liquent.

Spec: liquent/06_Backtesting/Backtesting_Framework_Spec.md
ADR: liquent/10_Decisions/ADR-003_Backtesting_Before_Automation.md

Reproduzierbare Läufe mit realistischem Kostenmodell. Nur Gerüst.
"""

from .comparison_reporting import normalize_comparison, render_comparison_markdown
from .runner import BacktestRunner, CostModel

__all__ = [
    "BacktestRunner",
    "CostModel",
    "normalize_comparison",
    "render_comparison_markdown",
]
