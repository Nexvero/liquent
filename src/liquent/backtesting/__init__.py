"""Backtesting-Framework für Liquent.

Spec: liquent/06_Backtesting/Backtesting_Framework_Spec.md
ADR: liquent/10_Decisions/ADR-003_Backtesting_Before_Automation.md

Reproduzierbare Läufe mit realistischem Kostenmodell. Nur Gerüst.
"""

from .runner import BacktestRunner, CostModel

__all__ = ["BacktestRunner", "CostModel"]
