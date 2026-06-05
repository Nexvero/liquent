"""Backtesting-Metriken — reine Funktionen (LQ-005 Phase 1).

Spec: liquent/06_Backtesting/Backtesting_Framework_Spec.md
Task: liquent/11_Tasks/LQ-005_Backtesting_Framework.md

Diese Datei bildet die *Grundlage* des Backtesting-Frameworks: eine leichte,
immutable Trade-Struktur, eine reine Kostenberechnung und die Mindestmetriken
aus LQ-005. Bewusst NICHT enthalten (folgt in späteren Phasen):

- keine Runner-Lauflogik (Phase 2),
- keine Datenquelle / kein CSV-Lader (Phase 3, LQ-003),
- keine Strategie (Phase 4),
- kein Paper-/Live-Trading, keine Netzwerk-Calls.

Alle Funktionen sind rein (keine Seiteneffekte, kein I/O, deterministisch) und
nutzen ausschließlich die Standardbibliothek.

Konvention für "Gewinn"/"Verlust": maßgeblich ist ``TradeResult.net_pnl``
(also nach Kosten), damit Metriken die realen Kostenannahmen widerspiegeln
(Akzeptanzkriterium LQ-005: kein Ergebnis ohne Kostenannahmen).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:  # nur für Typannotation — vermeidet jede Import-Kopplung/Zyklen
    from .runner import CostModel


# --------------------------------------------------------------------------- #
# Trade-Struktur
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class TradeResult:
    """Ergebnis eines abgeschlossenen (simulierten) Trades.

    Leichte, immutable Datenstruktur OHNE Marktlogik. Sie hält nur das, was die
    Metriken brauchen. Preise/Mengen werden hier nicht neu berechnet; ``net_pnl``
    etc. werden vom (späteren) Runner befüllt.

    Felder:
        entry_time:    ISO-8601-UTC-Zeitstempel des Einstiegs (oder None).
        exit_time:     ISO-8601-UTC-Zeitstempel des Ausstiegs (oder None).
        entry_price:   Einstiegspreis.
        exit_price:    Ausstiegspreis.
        quantity:      Gehandelte Menge (>= 0).
        side:          "long" oder "short".
        gross_pnl:     Roh-PnL vor Kosten.
        costs:         Summe der Handelskosten (siehe calculate_trade_costs).
        net_pnl:       PnL nach Kosten (maßgeblich für Metriken).
        r_multiple:    Ergebnis in R (PnL / initiales Risiko); 0.0 falls unbekannt.
        duration_bars: Haltedauer in Bars (>= 0).
    """

    entry_price: float
    exit_price: float
    quantity: float
    side: str
    gross_pnl: float = 0.0
    costs: float = 0.0
    net_pnl: float = 0.0
    r_multiple: float = 0.0
    duration_bars: int = 0
    entry_time: str | None = None
    exit_time: str | None = None

    def __post_init__(self) -> None:
        # Minimale, fail-safe Validierung — keine komplexe Marktlogik.
        if self.side not in ("long", "short"):
            raise ValueError(
                f"side muss 'long' oder 'short' sein, nicht {self.side!r}"
            )
        if self.quantity < 0:
            raise ValueError("quantity darf nicht negativ sein")
        if self.duration_bars < 0:
            raise ValueError("duration_bars darf nicht negativ sein")


# --------------------------------------------------------------------------- #
# Kostenberechnung (reine Funktion)
# --------------------------------------------------------------------------- #
def calculate_trade_costs(
    price: float, quantity: float, cost_model: "CostModel"
) -> float:
    """Berechnet die Handelskosten für eine Ausführung (rein, deterministisch).

    Einheiten-Konvention für Phase 1 (nutzt die vorhandenen ``CostModel``-Felder
    aus ``runner.py`` — KEINE neue, inkompatible Struktur):

        cost_model.fee_rate  -> Anteil des Notional (0.001 = 0.1 %).
        cost_model.spread    -> absoluter Preisaufschlag pro Einheit.
        cost_model.slippage  -> Anteil des Notional (0.0005 = 0.05 %).
                                (entspricht dem im Plan genannten "slippage_rate")

    Formel::

        notional      = abs(price * quantity)
        fee_cost      = notional * fee_rate
        spread_cost   = abs(quantity) * spread
        slippage_cost = notional * slippage
        total_cost    = fee_cost + spread_cost + slippage_cost

    Kosten sind stets >= 0 (Beträge). Vorzeichenbehaftete Verrechnung mit dem
    PnL ist Sache des Runners (Phase 2), nicht dieser Funktion.
    """
    notional = abs(price * quantity)
    fee_cost = notional * cost_model.fee_rate
    spread_cost = abs(quantity) * cost_model.spread
    slippage_cost = notional * cost_model.slippage
    return fee_cost + spread_cost + slippage_cost


# --------------------------------------------------------------------------- #
# Mindestmetriken (LQ-005)
# --------------------------------------------------------------------------- #
def number_of_trades(trades: Sequence[TradeResult]) -> int:
    """Gesamtzahl abgeschlossener Trades."""
    return len(trades)


def win_rate(trades: Sequence[TradeResult]) -> float:
    """Anteil gewinnender Trades (net_pnl > 0). Leere Liste -> 0.0."""
    if not trades:
        return 0.0
    wins = sum(1 for t in trades if t.net_pnl > 0)
    return wins / len(trades)


def profit_factor(trades: Sequence[TradeResult]) -> float:
    """Bruttogewinn / Bruttoverlust (auf net_pnl-Basis).

    Sonderfälle:
        - leere Liste / keine Gewinne und keine Verluste -> 0.0
        - Gewinne vorhanden, aber keine Verluste          -> float("inf")
    """
    gross_profit = sum(t.net_pnl for t in trades if t.net_pnl > 0)
    gross_loss = -sum(t.net_pnl for t in trades if t.net_pnl < 0)  # positiver Betrag
    if gross_loss == 0.0:
        return float("inf") if gross_profit > 0.0 else 0.0
    return gross_profit / gross_loss


def max_drawdown(equity_curve: Sequence[float]) -> float:
    """Maximaler Peak-to-Trough-Rückgang der Equity-Kurve (absoluter Betrag).

    Liefert einen nicht-negativen Wert. Leere Kurve -> 0.0.
    """
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        drawdown = peak - equity
        if drawdown > max_dd:
            max_dd = drawdown
    return max_dd


def average_r_multiple(trades: Sequence[TradeResult]) -> float:
    """Durchschnittliches R-Multiple über alle Trades. Leere Liste -> 0.0."""
    if not trades:
        return 0.0
    return sum(t.r_multiple for t in trades) / len(trades)


def expectancy(trades: Sequence[TradeResult]) -> float:
    """Erwartungswert pro Trade = Mittelwert des net_pnl. Leere Liste -> 0.0."""
    if not trades:
        return 0.0
    return sum(t.net_pnl for t in trades) / len(trades)


def exposure_time(trades: Sequence[TradeResult], total_bars: int) -> float:
    """Anteil der Zeit im Markt = Σ(duration_bars) / total_bars (0.0–1.0+).

    Sonderfall: total_bars <= 0 -> 0.0 (keine Division durch 0).
    """
    if total_bars <= 0:
        return 0.0
    return sum(t.duration_bars for t in trades) / total_bars


def worst_losing_streak(trades: Sequence[TradeResult]) -> int:
    """Längste Folge aufeinanderfolgender Verlust-Trades (net_pnl < 0).

    Leere Liste -> 0.
    """
    longest = 0
    current = 0
    for t in trades:
        if t.net_pnl < 0:
            current += 1
            if current > longest:
                longest = current
        else:
            current = 0
    return longest


def best_trade(trades: Sequence[TradeResult]) -> float:
    """Größter Einzel-net_pnl. Leere Liste -> 0.0."""
    if not trades:
        return 0.0
    return max(t.net_pnl for t in trades)


def worst_trade(trades: Sequence[TradeResult]) -> float:
    """Kleinster Einzel-net_pnl (größter Verlust). Leere Liste -> 0.0."""
    if not trades:
        return 0.0
    return min(t.net_pnl for t in trades)
