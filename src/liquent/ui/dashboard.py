"""Dashboard MVP — Platzhalter zur Anzeige von Kennzahlen.

Spec: liquent/08_UI/Dashboard_MVP_Spec.md

Zweck: Liquidität und Strategieverhalten verständlich darstellen, OHNE zu
impulsiver Ausführung zu verleiten.

MVP-Funktionen (laut Spec): Liquiditätskennzahlen (Spread, Depth, Imbalance),
Signale + zugehörige RiskDecisions, Backtest-/Experiment-Ergebnisse,
Phasenstatus (Backtesting / Paper-Trading).

Nicht im MVP (verbindlich): KEINE Order-Buttons, keine Live-Handelsknöpfe,
keine Konfiguration sensibler Zugangsdaten. Dieses Modul enthält daher bewusst
keine Ausführungs-Funktion.
"""

from __future__ import annotations

from ..domain.models import LiquidityMetric, RiskDecision, Signal


class Dashboard:
    """Reiner Anzeige-Platzhalter (keine Ausführungslogik).

    Die Methoden liefern darstellbare Strukturen/Strings; sie lösen keinerlei
    Aktion am Markt aus. Risiko- und Drawdown-Anzeigen sind laut Spec prominent
    zu zeigen.
    """

    def render_liquidity(self, metric: LiquidityMetric) -> dict[str, float]:
        """Bereitet Liquiditätskennzahlen für die Anzeige auf (Spread/Depth/Imbalance)."""
        return {
            "spread": metric.spread,
            "depth": metric.depth,
            "imbalance": metric.imbalance,
        }

    def render_signal(self, signal: Signal, decision: RiskDecision) -> dict[str, object]:
        """Zeigt ein Signal zusammen mit seiner RiskDecision (Nachvollziehbarkeit)."""
        return {
            "direction": signal.direction.value,
            "strength": signal.strength,
            "approved": decision.approved,
            "size": decision.size,
            "reason": decision.reason,
        }

    def render_phase_status(
        self, backtesting_done: bool, paper_trading_active: bool
    ) -> dict[str, str]:
        """Stellt den Phasenstatus klar erkennbar dar (ADR-003-Phasenfolge).

        # TODO(spec): Konkrete UI-Technologie (Web, TUI, Notebook) ist im MVP
        #   nicht festgelegt. Diese Methode liefert vorerst nur strukturierte
        #   Statuswerte, kein Rendering-Backend.
        """
        return {
            "backtesting": "abgeschlossen" if backtesting_done else "offen",
            "paper_trading": "aktiv" if paper_trading_active else "inaktiv",
        }
