"""Paper-Trading-Engine — ausschließlich Simulation.

Spec: liquent/07_Bot/Paper_Trading_Spec.md
ADR: liquent/10_Decisions/ADR-003_Backtesting_Before_Automation.md

Sicherheits-Invarianten dieses Moduls (verbindlich):
- KEINE produktive Ausführung. Es existiert KEIN Code-Pfad zu echter
  Order-Ausführung oder zu einem Broker/einer Börse.
- Jede simulierte Order durchläuft zwingend die Risk Engine (Risk-First).
- Vollständiges Logging aller Signale, RiskDecisions und simulierten Positionen.
- Paper-Trading startet erst, wenn ein Backtest mit dokumentierten Metriken
  vorliegt (Freigabekriterium der Spec).
"""

from __future__ import annotations

import logging

from ..domain.models import Position, PositionStatus, RiskDecision, Signal
from ..risk.engine import AccountState, RiskEngine

logger = logging.getLogger("liquent.bot.paper_trading")


class PaperTradingEngine:
    """Simuliert Ausführung gegen Live-/Replay-Daten — niemals real.

    Diese Engine kann konstruktionsbedingt keine echte Order auslösen: es gibt
    keinen entsprechenden Aufruf, keine Zugangsdaten und keinen Netzwerkpfad.
    """

    def __init__(self, risk_engine: RiskEngine, backtest_completed: bool = False) -> None:
        # Freigabekriterium (ADR-003): ohne dokumentierten Backtest kein Start.
        self.risk_engine = risk_engine
        self.backtest_completed = backtest_completed

    def process_signal(
        self, signal: Signal, account_state: AccountState
    ) -> RiskDecision:
        """Verarbeitet ein Signal als Simulation (Risk-First, vollständiges Log).

        Gibt die RiskDecision zurück. Eröffnet bei Freigabe ausschließlich eine
        SIMULIERTE Position (kein realer Effekt).

        # TODO(spec): Marktdaten-Anbindung (Live/Replay), Slippage-Beobachtung
        #   und der Vergleich Paper vs. Backtest folgen in LQ-006. Hier nur der
        #   sichere Kontrollfluss.
        """
        if not self.backtest_completed:
            decision = RiskDecision(
                approved=False,
                size=0.0,
                reason="Freigabekriterium nicht erfüllt: kein dokumentierter Backtest (ADR-003)",
            )
            logger.info("paper-trading gesperrt: %s", decision.reason)
            return decision

        # Risk-First: verbindlicher Durchlauf durch die Risk Engine.
        decision = self.risk_engine.evaluate(signal, account_state)
        logger.info(
            "signal=%s decision=approved:%s size:%s reason:%s",
            signal,
            decision.approved,
            decision.size,
            decision.reason,
        )

        if decision.approved:
            # Nur SIMULIERT — keine reale Ausführung.
            simulated = self._open_simulated_position(signal, decision)
            logger.info("simulierte Position eröffnet: %s", simulated)

        return decision

    def _open_simulated_position(
        self, signal: Signal, decision: RiskDecision
    ) -> Position | None:
        """Erzeugt ein Position-Objekt rein zu Logging-/Simulationszwecken.

        # TODO(spec): Instrument-Zuordnung und Entry-Preis stammen später aus
        #   den Marktdaten (LQ-006). Bis dahin nicht konstruierbar -> None.
        """
        # Ohne Marktdaten/Instrument kann keine sinnvolle Position gebildet
        # werden; bewusst None statt Platzhalterwerte zu erfinden.
        _ = (signal, decision)
        return None
