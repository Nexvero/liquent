"""Paper-Trading für Liquent.

Spec: liquent/07_Bot/Paper_Trading_Spec.md
ADR: liquent/10_Decisions/ADR-003_Backtesting_Before_Automation.md

Ausschließlich Simulation. Keinerlei Verbindung zu echter Order-Ausführung.
"""

from .paper_trading import PaperTradingEngine

__all__ = ["PaperTradingEngine"]
