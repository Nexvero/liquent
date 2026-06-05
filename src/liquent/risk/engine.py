"""Risk Engine — zentrale Risikoprüfung für Liquent.

Spec: liquent/05_Risk/Risk_Engine_Spec.md
ADR: liquent/10_Decisions/ADR-002_Risk_First_Execution.md

Die Risk Engine ist Pflichtkomponente und Single Point of Control: jedes Signal
durchläuft ``evaluate`` und erhält genau eine RiskDecision.

Leitregeln aus der Spec (in diesem Skeleton als dokumentierte Regeln + Stub,
noch OHNE reale Sizing-Implementierung):

- Fail-safe: bei Unsicherheit oder Fehlkonfiguration -> ablehnen statt zulassen.
- Harte Limits: max. Positionsgröße, max. Gesamtexposure.
- Verlustserien-Regel (Invariante): nach aufeinanderfolgenden Verlusten wird
  das Risiko NIE erhöht.
- Tages-/Drawdown-Stopp: Pausieren bei Überschreiten definierter Schwellen.
- Jede Ablehnung trägt eine ``reason``.
- Deterministisch und testbar; keine produktive Ausführung in dieser Phase.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.models import Direction, RiskDecision, Signal


@dataclass(frozen=True)
class RiskLimits:
    """Harte Risiko-Grenzen (Konfiguration).

    Werte sind konservative Platzhalter. Fail-safe: nicht-positive oder
    widersprüchliche Limits führen in ``evaluate`` zur Ablehnung.

    # TODO(spec): Risk_Engine_Spec nennt die Regeln ("fixes Risiko pro Trade",
    #   max. Positionsgröße, max. Exposure, Drawdown-Stopp), aber keine
    #   konkreten Zahlen. Die Defaults hier sind Platzhalter und in einem
    #   Folge-Task fachlich festzulegen.
    """

    max_position_size: float = 0.0
    max_total_exposure: float = 0.0
    risk_per_trade: float = 0.0
    max_daily_drawdown: float = 0.0
    # LQ-004 Phase 1 (additiv, fail-safe Defaults): vorbereitete Felder für das
    # spätere prozentuale Sizing. Werden in dieser Phase NICHT ausgewertet —
    # ``sizing_mode`` bleibt "absolute"; ``evaluate`` ist unverändert.
    risk_per_trade_pct: float = 0.0
    max_position_notional: float = 0.0
    max_daily_loss: float = 0.0
    max_losing_streak: int = 0
    sizing_mode: str = "absolute"


@dataclass(frozen=True)
class AccountState:
    """Aktueller Konto-/Exposure-Zustand (Eingang der Risikoprüfung).

    Felder entsprechen den in der Spec genannten Eingangsgrößen.
    """

    equity: float = 0.0
    current_exposure: float = 0.0
    consecutive_losses: int = 0
    day_drawdown: float = 0.0
    # LQ-004 Phase 1 (additiv, Default 0.0): realisierter Tagesverlust, später
    # für das ``max_daily_loss``-Limit. In dieser Phase ungenutzt.
    day_realized_loss: float = 0.0


def _reject(reason: str) -> RiskDecision:
    """Hilfsfunktion: einheitliche Ablehnung mit Begründung (size = 0)."""
    return RiskDecision(approved=False, size=0.0, reason=reason)


class RiskEngine:
    """Prüft Signale gegen Limits und Risikoregeln (fail-safe).

    Akzeptanzkriterium der Spec: Jedes Signal erzeugt genau eine RiskDecision.
    """

    def __init__(self, limits: RiskLimits | None = None) -> None:
        # Fail-safe: ohne explizite Limits gelten die (nicht freigebenden)
        # Defaults, die jede Order ablehnen, bis eine Konfiguration vorliegt.
        self.limits = limits if limits is not None else RiskLimits()

    def evaluate(
        self,
        signal: Signal,
        account_state: AccountState,
        reference_price: float | None = None,
    ) -> RiskDecision:
        """Bewertet ein Signal und gibt genau eine RiskDecision zurück.

        Dispatch nach ``limits.sizing_mode``:
        - ``"absolute"`` (Default): unverändertes Verhalten (LQ-005);
          ``reference_price`` wird ignoriert.
        - ``"percent_risk"`` (LQ-004 Phase 2): prozentuales Sizing mit
          Pflicht-``reference_price`` und Pflicht-``signal.stop_price``.
        - unbekannter Modus: fail-safe ablehnen.

        Fail-safe-Reihenfolge: zuerst alle Ablehnungsgründe prüfen; nur wenn
        keiner greift, wird (konservativ) freigegeben. Risiko wird nach
        Verlustserien NIE erhöht (kein Martingale).
        """
        mode = self.limits.sizing_mode
        if mode == "absolute":
            return self._evaluate_absolute(signal, account_state)
        if mode == "percent_risk":
            return self._evaluate_percent_risk(signal, account_state, reference_price)
        return _reject(f"unbekannter sizing_mode {mode!r} (fail-safe)")

    def _evaluate_absolute(
        self, signal: Signal, account_state: AccountState
    ) -> RiskDecision:
        """Bisheriges absolutes Sizing (LQ-005) — unverändert.

        # TODO(spec): Reale Position-Sizing-Formel ist nicht spezifiziert.
        #   Dieser Stub berechnet KEINE produktive Größe; er gibt im
        #   Freigabefall die durch das Limit gedeckelte Risiko-Größe zurück.
        """
        # 1) Fehlendes/ungültiges Signal -> ablehnen (Risk-Engine-Test deckt dies ab).
        if signal is None:
            return _reject("kein Signal übergeben")
        if signal.direction == Direction.FLAT:
            return _reject("FLAT-Signal: keine Ausführung erforderlich")
        if signal.strength <= 0.0:
            return _reject("Signalstärke <= 0: keine valide Handlungsempfehlung")

        # 2) Fehlkonfiguration der Limits -> ablehnen (fail-safe statt fail-open).
        if (
            self.limits.max_position_size <= 0.0
            or self.limits.max_total_exposure <= 0.0
            or self.limits.risk_per_trade <= 0.0
        ):
            return _reject(
                "Risk-Limits nicht konfiguriert oder nicht positiv (fail-safe)"
            )

        # 3) Drawdown-/Tagesstopp -> pausieren.
        if (
            self.limits.max_daily_drawdown > 0.0
            and account_state.day_drawdown >= self.limits.max_daily_drawdown
        ):
            return _reject("Tages-/Drawdown-Stopp erreicht")

        # 4) Exposure-Limit bereits ausgeschöpft.
        if account_state.current_exposure >= self.limits.max_total_exposure:
            return _reject("maximales Gesamtexposure erreicht")

        # 5) Verlustserien-Regel: Risiko NIE erhöhen. In dieser Phase wird die
        #    Größe daher höchstens auf dem Basis-Risiko gehalten, niemals
        #    skaliert. Invariante: consecutive_losses erhöht das Risiko nicht.
        base_risk = self.limits.risk_per_trade
        # (Keine Aufstockung nach Verlustserie — bewusst kein Faktor > 1.)
        proposed = min(base_risk, self.limits.max_position_size)

        # 6) Restliches Exposure-Budget respektieren.
        remaining = self.limits.max_total_exposure - account_state.current_exposure
        size = min(proposed, remaining)
        if size <= 0.0:
            return _reject("kein freies Risikobudget verfügbar")

        return RiskDecision(
            approved=True,
            size=size,
            reason="innerhalb der konfigurierten Limits freigegeben (Stub-Sizing)",
        )

    def _evaluate_percent_risk(
        self,
        signal: Signal,
        account_state: AccountState,
        reference_price: float | None,
    ) -> RiskDecision:
        """Prozentuales Risiko-Sizing (LQ-004 Phase 2), fail-safe.

        risk_amount   = equity * risk_per_trade_pct
        stop_distance = abs(reference_price - signal.stop_price)
        raw_size      = risk_amount / stop_distance
        notional      = size * reference_price

        Größe wird durch ``max_position_size``, ``max_position_notional`` und
        das freie ``max_total_exposure`` ausschließlich verkleinert (nie
        vergrößert). Jede greifende Grenze wird in den Audit-Flags vermerkt.
        """
        # 1) Signal-Grundprüfung.
        if signal is None:
            return _reject("kein Signal übergeben")
        if signal.direction == Direction.FLAT:
            return _reject("FLAT-Signal: keine Ausführung erforderlich")
        if signal.strength <= 0.0:
            return _reject("Signalstärke <= 0: keine valide Handlungsempfehlung")

        # 2) Referenzpreis ist im percent_risk-Modus Pflicht.
        if reference_price is None:
            return _reject("percent_risk: reference_price fehlt (fail-safe)")
        if reference_price <= 0.0:
            return _reject("percent_risk: reference_price <= 0 (fail-safe)")

        # 3) Stop-Preis ist Pflicht (keine impliziten Stops raten).
        if signal.stop_price is None:
            return _reject("percent_risk: stop_price fehlt (fail-safe)")
        if signal.stop_price <= 0.0:
            return _reject("percent_risk: stop_price <= 0 (fail-safe)")

        # 4) Konto-/Limit-Konfiguration (fail-safe statt fail-open).
        if account_state.equity <= 0.0:
            return _reject("percent_risk: equity <= 0 (fail-safe)")
        if self.limits.risk_per_trade_pct <= 0.0:
            return _reject("percent_risk: risk_per_trade_pct <= 0 (fail-safe)")
        if self.limits.risk_per_trade_pct > 1.0:
            return _reject("percent_risk: risk_per_trade_pct > 1.0 (fail-safe)")
        if self.limits.max_position_size <= 0.0:
            return _reject("Risk-Limits: max_position_size <= 0 (fail-safe)")
        if self.limits.max_total_exposure <= 0.0:
            return _reject("Risk-Limits: max_total_exposure <= 0 (fail-safe)")
        if self.limits.max_daily_drawdown <= 0.0:
            return _reject("Risk-Limits: max_daily_drawdown <= 0 (fail-safe)")

        # 5) Stop-Seite konsistent zur Richtung; Stop-Distanz > 0.
        if signal.direction == Direction.LONG and not signal.stop_price < reference_price:
            return _reject("percent_risk: Long-Stop muss < reference_price sein")
        if signal.direction == Direction.SHORT and not signal.stop_price > reference_price:
            return _reject("percent_risk: Short-Stop muss > reference_price sein")
        stop_distance = abs(reference_price - signal.stop_price)
        if stop_distance == 0.0:
            return _reject("percent_risk: stop_distance == 0 (fail-safe)")

        # 6) Stopp-/Pausen-Regeln (Risk-First; keine Risikoerhöhung nach Verlusten).
        if account_state.day_drawdown >= self.limits.max_daily_drawdown:
            return _reject("Tages-/Drawdown-Stopp erreicht")
        if (
            self.limits.max_daily_loss > 0.0
            and account_state.day_realized_loss >= self.limits.max_daily_loss
        ):
            return _reject("max_daily_loss erreicht")
        if (
            self.limits.max_losing_streak > 0
            and account_state.consecutive_losses >= self.limits.max_losing_streak
        ):
            return _reject("max_losing_streak erreicht (Pause, keine Risikoerhöhung)")
        if account_state.current_exposure >= self.limits.max_total_exposure:
            return _reject("maximales Gesamtexposure erreicht")

        # 7) Sizing: Risiko-Betrag / Stop-Distanz, danach ausschließlich kappen.
        risk_amount = account_state.equity * self.limits.risk_per_trade_pct
        size = risk_amount / stop_distance

        capped_by_max_position = False
        capped_by_max_notional = False
        capped_by_total_exposure = False

        # Cap 1: maximale Positionsgröße (Einheiten).
        if size > self.limits.max_position_size:
            size = self.limits.max_position_size
            capped_by_max_position = True

        # Cap 2: maximales Positions-Notional (nur falls konfiguriert).
        if (
            self.limits.max_position_notional > 0.0
            and size * reference_price > self.limits.max_position_notional
        ):
            size = self.limits.max_position_notional / reference_price
            capped_by_max_notional = True

        # Cap 3: verbleibendes Gesamtexposure-Budget.
        remaining_exposure = (
            self.limits.max_total_exposure - account_state.current_exposure
        )
        if size * reference_price > remaining_exposure:
            size = remaining_exposure / reference_price
            capped_by_total_exposure = True

        if size <= 0.0:
            return _reject("percent_risk: kein freies Risikobudget verfügbar")

        notional = size * reference_price

        return RiskDecision(
            approved=True,
            size=size,
            reason="percent_risk: innerhalb der konfigurierten Limits freigegeben",
            risk_amount=risk_amount,
            stop_distance=stop_distance,
            notional=notional,
            capped_by_max_position=capped_by_max_position,
            capped_by_max_notional=capped_by_max_notional,
            capped_by_total_exposure=capped_by_total_exposure,
        )
