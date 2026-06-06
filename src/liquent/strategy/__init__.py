"""Liquent-Strategien (LQ-006).

Regelbasierte, deterministische Strategien, die die ``Strategy``-Schnittstelle
des Backtesting-Runners erfüllen. Keine Live-Ausführung, keine Optimierung,
keine Profitabilitätsaussage.
"""

from liquent.strategy.mid_breakout import MidBreakoutStrategy

__all__ = ["MidBreakoutStrategy"]
