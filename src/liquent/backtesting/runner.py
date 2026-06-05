"""Backtesting-Runner — reproduzierbare Läufe (LQ-005 Phase 2).

Spec: liquent/06_Backtesting/Backtesting_Framework_Spec.md
ADR: liquent/10_Decisions/ADR-003_Backtesting_Before_Automation.md

Anforderungen aus der Spec:
- Einlesen historischer MarketData / OrderBookSnapshots.
- Deterministische, reproduzierbare Läufe (feste Seeds, versionierte Parameter).
- Realistisches Kostenmodell als Parameter: Gebühren, Spread, Slippage.
- Anbindung der Risk Engine im Backtest (Risk-First auch hier, ADR-002).
- Ausgabe standardisierter Metriken; jeder Lauf wird als Experiment dokumentiert.

Sicherheit: keine Live-Ausführung, keine Netzwerk-Calls, keine Aussage über
zukünftige Profitabilität. Der Runner ist rein deterministisch — keine
Wall-Clock-Zeit, kein ungeseedeter Zufall.

Modellannahmen dieser Phase (per Freigabe festgelegt):
- Richtung: Long & Short.
- Trade-Simulation: Close-to-Close — pro Signal ein Trade, Entry zum Mid-Preis
  des referenzierten Bars, Exit zum Mid-Preis des Folge-Bars (Haltedauer = 1 Bar).
- Referenzpreis = Mid = (bid + ask) / 2 aus ``MarketData`` (das Domänenmodell
  liefert bid/ask, kein OHLC).
- ``risk_per_trade`` wird als absolute Größe interpretiert (Status quo der Risk
  Engine; keine Änderung an engine.py).
- Strategie (Phase 4): injizierbare ``Strategy`` mit
  ``generate_signals(market_data) -> Sequence[Signal]``. Default bleibt der
  deterministische Momentum-Stub. Jedes Signal referenziert seinen Bar über
  ``Signal.timestamp``; Entry an diesem Bar, Exit am Folge-Bar. Risk-First gilt
  unverändert — jedes ausführbare Signal MUSS durch die Risk Engine.

# TODO(spec): R-Multiple ist hier ein dokumentierter Proxy (net_pnl / size),
#   solange keine Stop-basierte Risiko-Definition vorliegt (gehört zu LQ-004).
# TODO(spec): Datenvalidierung (Schema/Reihenfolge/Duplikate/Lücken) folgt mit
#   dem CSV-Lader in Phase 3 (LQ-003); hier nur minimale Robustheit.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional, Protocol, Sequence, runtime_checkable

from ..data.sources import DataSource
from ..domain.models import Direction, MarketData, Signal
from ..risk.engine import AccountState, RiskEngine
from .metrics import (
    TradeResult,
    average_r_multiple,
    best_trade,
    calculate_trade_costs,
    expectancy,
    exposure_time,
    max_drawdown,
    number_of_trades,
    profit_factor,
    win_rate,
    worst_losing_streak,
    worst_trade,
)

@runtime_checkable
class Strategy(Protocol):
    """Einfache, injizierbare Strategie-Schnittstelle (LQ-005 Phase 4).

    Eine Strategie erhält die vollständige (validierte, aufsteigend sortierte)
    Bar-Sequenz und liefert eine Sequenz von ``Signal``-Objekten. Jedes Signal
    referenziert seinen Bar über ``Signal.timestamp``. Bewusst nur eine
    Schnittstelle — KEINE echte Handelslogik, keine Bewertung, keine
    Optimierung. Der Runner führt jedes Signal unverändert über die Risk Engine
    aus (Risk-First).
    """

    def generate_signals(self, market_data: Sequence[MarketData]) -> Sequence[Signal]:
        """Erzeugt Signale zur gegebenen Bar-Sequenz (rein, deterministisch)."""
        ...


@dataclass(frozen=True)
class CostModel:
    """Realistisches Kostenmodell als Parameter eines Laufs.

    Felder gemäß Spec: Gebühren, Spread, Slippage. Einheiten (Phase 1/2):
    - fee_rate: Anteil des Notional (0.001 = 0.1 %).
    - spread:   absoluter Preisaufschlag pro Einheit.
    - slippage: Anteil des Notional (0.0005 = 0.05 %).

    # TODO(spec): Gebührenstaffeln / komplexeres Slippage-Modell sind in
    #   06_Backtesting weiter zu präzisieren.
    """

    fee_rate: float = 0.0
    spread: float = 0.0
    slippage: float = 0.0


@dataclass(frozen=True)
class BacktestResult:
    """Standardisiertes, immutables Ergebnis eines Backtest-Laufs (Phase 2).

    Leichte Ergebnisstruktur gemäß LQ-005: hält Gate-Zählungen (Risk-First),
    die Equity-Entwicklung, die simulierten Trades und die berechneten
    Metriken. Bewusst ohne mutable Defaults — alle Felder sind Pflicht und
    werden vom Runner explizit befüllt. ``parameters`` enthält ausschließlich
    skalare Werte (reproduzierbare, flach serialisierbare Lauf-Parameter).

    Felder:
        experiment_id:    Deterministische ID des Laufs (Hash der Parameter).
        number_of_trades: Anzahl abgeschlossener (simulierter) Trades.
        approved_signals: Von der Risk Engine freigegebene Signale.
        rejected_signals: Von der Risk Engine abgelehnte Signale.
        starting_equity:  Start-Equity zu Beginn des Laufs.
        ending_equity:    End-Equity nach allen Trades.
        equity_curve:     Equity nach jedem Schritt (beginnt mit starting_equity).
        metrics:          Standardmetriken aus ``metrics.py``.
        trades:           Die simulierten ``TradeResult``-Einträge (immutable).
        parameters:       Reproduzierbare, skalare Lauf-Parameter.
    """

    experiment_id: str
    number_of_trades: int
    approved_signals: int
    rejected_signals: int
    starting_equity: float
    ending_equity: float
    equity_curve: tuple[float, ...]
    metrics: dict[str, float]
    trades: tuple[TradeResult, ...]
    parameters: dict[str, str | int | float | bool]


def _deterministic_experiment_id(parameters: dict[str, object]) -> str:
    """Reproduzierbare Lauf-ID aus den (skalaren) Parametern.

    Keine Wall-Clock, kein Zufall — gleicher Input ergibt dieselbe ID. Dient
    nur der Identifikation/Dokumentation eines Experiments, nicht der Sicherheit.
    """
    canonical = "|".join(f"{key}={parameters[key]}" for key in sorted(parameters))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"lq005-{digest[:12]}"


def _mid(bar: MarketData) -> float:
    """Referenzpreis eines Bars = Mittelkurs zwischen bid und ask."""
    return (bar.bid + bar.ask) / 2.0


def default_momentum_stub(index: int, bars: Sequence[MarketData]) -> Optional[Signal]:
    """Deterministischer Beispiel-Signal-Stub (keine echte Strategie).

    Regel: steigt der Mid-Preis gegenüber dem Vorgänger -> LONG, fällt er ->
    SHORT, sonst kein Signal. Strength fix 1.0 (Annahme Skala 0..1). Dient nur
    dazu, die Pipeline + Risk-Gate + Metriken testbar zu machen.
    """
    if index <= 0:
        return None
    prev = _mid(bars[index - 1])
    cur = _mid(bars[index])
    if cur > prev:
        direction = Direction.LONG
    elif cur < prev:
        direction = Direction.SHORT
    else:
        return None
    return Signal(timestamp=bars[index].timestamp, direction=direction, strength=1.0)


class MomentumStubStrategy:
    """Default-Strategie: deterministischer Momentum-Stub (keine echte Strategie).

    Wrappt ``default_momentum_stub`` über die gesamte Bar-Sequenz und erfüllt
    damit die ``Strategy``-Schnittstelle. Verhalten identisch zu Phase 2/3:
    steigt der Mid-Preis gegenüber dem Vorgänger -> LONG, fällt er -> SHORT,
    sonst kein Signal. Es werden nur Signale für Bars mit Folge-Bar erzeugt
    (Close-to-Close braucht einen Exit-Bar). Keine Aussage über Profitabilität.
    """

    def generate_signals(self, market_data: Sequence[MarketData]) -> list[Signal]:
        bars = list(market_data)
        signals: list[Signal] = []
        # Entry-Bar braucht einen Folge-Bar -> Index läuft nur bis n-2.
        for index in range(len(bars) - 1):
            signal = default_momentum_stub(index, bars)
            if signal is not None:
                signals.append(signal)
        return signals


class BacktestRunner:
    """Reproduzierbarer Backtest-Lauf (Close-to-Close, Risk-First).

    Akzeptanzkriterium der Spec: gleicher Input -> gleiches Ergebnis. Der Lauf
    ist deterministisch; ``seed`` wird zur Reproduzierbarkeit im Experiment
    festgehalten (aktuell ohne RNG-Bedarf).

    Die Strategie ist über den Konstruktor injizierbar (``strategy=``). Ohne
    Angabe greift der deterministische ``MomentumStubStrategy``-Default; jede
    injizierte Strategie durchläuft dieselbe Risk-First-Pipeline.
    """

    def __init__(
        self,
        source: DataSource,
        risk_engine: RiskEngine,
        cost_model: CostModel,
        seed: int = 0,
        strategy: Strategy | None = None,
        initial_equity: float = 0.0,
        hypothese: str = "Deterministischer Backtest-Stub (LQ-005 Phase 2)",
    ) -> None:
        # Risk-First: Backtests laufen verbindlich über die Risk Engine.
        self.source = source
        self.risk_engine = risk_engine
        self.cost_model = cost_model
        self.seed = seed
        # Injizierbare Strategie (testbar); Default = deterministischer Momentum-Stub.
        self.strategy: Strategy = strategy if strategy is not None else MomentumStubStrategy()
        self.initial_equity = initial_equity
        self.hypothese = hypothese

    def run(self) -> BacktestResult:
        """Führt einen deterministischen Close-to-Close-Lauf aus.

        Ablauf:
            Strategie erzeugt Signale über die Bar-Sequenz -> Signale werden
            ihren Bars zugeordnet (fail-safe validiert) -> je Signal: Risk
            Engine (Pflicht) -> bei Freigabe Fill zum Mid-Preis, Kosten
            anwenden, Trade schließen, Equity/State aktualisieren. Liefert ein
            ``BacktestResult`` mit Gate-Zählungen, Equity-Kurve, Trades,
            Parametern und Metriken.
        """
        bars = list(self.source.market_data())

        trades: list[TradeResult] = []
        equity = self.initial_equity
        equity_curve: list[float] = [equity]
        peak = equity
        consecutive_losses = 0
        signals_total = 0
        approved = 0
        rejected = 0

        # Phase 4: Strategie liefert Signale über die gesamte (sortierte)
        # Bar-Sequenz; jedes ausführbare Signal wird seinem Entry-Bar zugeordnet.
        raw_signals = self.strategy.generate_signals(bars)
        executable = self._resolve_signals(raw_signals, bars)

        for index, signal in executable:
            signals_total += 1

            # Entry-/Referenzpreis VOR dem Gate bestimmen — identisch zum Fill.
            # Wird der Risk Engine als reference_price übergeben (LQ-004 Phase 3);
            # im Default-Modus "absolute" ignoriert die Engine den Wert.
            entry_price = _mid(bars[index])
            exit_price = _mid(bars[index + 1])

            # Risk-First: jedes Signal MUSS durch die Risk Engine (keine Umgehung).
            # current_exposure = 0.0: Close-to-Close hält nie überlappende Positionen.
            account_state = AccountState(
                equity=equity,
                current_exposure=0.0,
                consecutive_losses=consecutive_losses,
                day_drawdown=peak - equity,
            )
            decision = self.risk_engine.evaluate(
                signal, account_state, reference_price=entry_price
            )
            if not decision.approved:
                rejected += 1
                continue
            approved += 1

            size = decision.size

            if signal.direction == Direction.LONG:
                gross_pnl = (exit_price - entry_price) * size
            else:  # Direction.SHORT (FLAT wird von der Risk Engine abgelehnt)
                gross_pnl = (entry_price - exit_price) * size

            # Kosten für Entry und Exit getrennt (Risk-First-konformes, reines Modell).
            costs = calculate_trade_costs(
                entry_price, size, self.cost_model
            ) + calculate_trade_costs(exit_price, size, self.cost_model)
            net_pnl = gross_pnl - costs

            # R-Multiple-Proxy (siehe Modul-TODO): net_pnl je Risiko-/Size-Einheit.
            r_multiple = net_pnl / size if size > 0 else 0.0

            trades.append(
                TradeResult(
                    entry_price=entry_price,
                    exit_price=exit_price,
                    quantity=size,
                    side=signal.direction.value,
                    gross_pnl=gross_pnl,
                    costs=costs,
                    net_pnl=net_pnl,
                    r_multiple=r_multiple,
                    duration_bars=1,
                    entry_time=bars[index].timestamp.isoformat(),
                    exit_time=bars[index + 1].timestamp.isoformat(),
                )
            )

            # State aktualisieren.
            equity += net_pnl
            equity_curve.append(equity)
            if equity > peak:
                peak = equity
            consecutive_losses = consecutive_losses + 1 if net_pnl < 0 else 0

        total_bars = len(bars)
        metriken: dict[str, float] = {
            "number_of_trades": number_of_trades(trades),
            "win_rate": win_rate(trades),
            "profit_factor": profit_factor(trades),
            "max_drawdown": max_drawdown(equity_curve),
            "average_r_multiple": average_r_multiple(trades),
            "expectancy": expectancy(trades),
            "exposure_time": exposure_time(trades, total_bars),
            "worst_losing_streak": worst_losing_streak(trades),
            "best_trade": best_trade(trades),
            "worst_trade": worst_trade(trades),
        }

        # Nur skalare, flach serialisierbare Parameter (str|int|float|bool).
        # Verschachtelte Strukturen werden bewusst aufgelöst. Leere Daten ->
        # "" statt None, um den skalaren Typ zu wahren.
        frictionless = (
            self.cost_model.fee_rate == 0.0
            and self.cost_model.spread == 0.0
            and self.cost_model.slippage == 0.0
        )
        parameter: dict[str, str | int | float | bool] = {
            "seed": self.seed,
            "hypothese": self.hypothese,
            "starting_equity": self.initial_equity,
            "direction_mode": "long_short",
            "trade_simulation": "close_to_close",
            "fee_rate": self.cost_model.fee_rate,
            "spread": self.cost_model.spread,
            "slippage": self.cost_model.slippage,
            "frictionless": frictionless,
            "max_position_size": self.risk_engine.limits.max_position_size,
            "max_total_exposure": self.risk_engine.limits.max_total_exposure,
            "risk_per_trade": self.risk_engine.limits.risk_per_trade,
            "max_daily_drawdown": self.risk_engine.limits.max_daily_drawdown,
            # LQ-004: Risk-Sizing-Parameter (dokumentarisch; Default-Modus absolute).
            "sizing_mode": self.risk_engine.limits.sizing_mode,
            "risk_per_trade_pct": self.risk_engine.limits.risk_per_trade_pct,
            "max_position_notional": self.risk_engine.limits.max_position_notional,
            "max_daily_loss": self.risk_engine.limits.max_daily_loss,
            "max_losing_streak": self.risk_engine.limits.max_losing_streak,
            "bars": total_bars,
            "strategy": type(self.strategy).__name__,
            "signals_total": signals_total,
            "period_start": bars[0].timestamp.isoformat() if bars else "",
            "period_end": bars[-1].timestamp.isoformat() if bars else "",
            # Sicherheits-/Modus-Invarianten dieser Phase (rein dokumentarisch):
            # kein Live-Trading, keine Netzwerk-Calls, kein Paper-Trading.
            "mode": "analysis",
            "live_execution": False,
            "network_calls": False,
            "paper_trading": False,
        }

        return BacktestResult(
            experiment_id=_deterministic_experiment_id(parameter),
            number_of_trades=len(trades),
            approved_signals=approved,
            rejected_signals=rejected,
            starting_equity=self.initial_equity,
            ending_equity=equity,
            equity_curve=tuple(equity_curve),
            metrics=metriken,
            trades=tuple(trades),
            parameters=parameter,
        )

    def _resolve_signals(
        self, raw_signals: Sequence[Signal], bars: Sequence[MarketData]
    ) -> list[tuple[int, Signal]]:
        """Validiert Strategie-Signale und ordnet sie ihren Entry-Bars zu.

        Fail-safe: ungültige Rückgaben führen zu einer klaren Exception, statt
        stillschweigend ignoriert zu werden:
            - ``None`` statt einer Sequenz -> ``TypeError``,
            - ein Element, das kein ``Signal`` ist -> ``TypeError``,
            - ein Signal mit ungültiger ``direction`` -> ``ValueError``,
            - ein Zeitstempel, der in den Bars nicht vorkommt -> ``ValueError``.

        Signale auf dem letzten Bar sind in der Close-to-Close-Simulation nicht
        ausführbar (kein Folge-Bar) und werden dokumentiert verworfen (sie
        zählen nicht als Signal). Das Ergebnis ist nach Entry-Bar-Index
        aufsteigend sortiert, damit die Equity-Entwicklung deterministisch und
        chronologisch bleibt.
        """
        if raw_signals is None:
            raise TypeError("Strategie lieferte None statt einer Signal-Sequenz")

        index_by_ts = {bar.timestamp: i for i, bar in enumerate(bars)}
        last_index = len(bars) - 1
        resolved: list[tuple[int, Signal]] = []
        for item in raw_signals:
            if not isinstance(item, Signal):
                raise TypeError(
                    f"Strategie lieferte ein ungültiges Signal-Objekt: {item!r} "
                    "(erwartet wird liquent.domain.models.Signal)"
                )
            if not isinstance(item.direction, Direction):
                raise ValueError(
                    f"Signal mit ungültiger direction: {item.direction!r}"
                )
            index = index_by_ts.get(item.timestamp)
            if index is None:
                raise ValueError(
                    f"Signal-Zeitstempel {item.timestamp!r} kommt in den "
                    "Marktdaten nicht vor"
                )
            if index >= last_index:
                # Letzter Bar: kein Folge-Bar für den Exit -> nicht ausführbar.
                continue
            resolved.append((index, item))

        resolved.sort(key=lambda pair: pair[0])
        return resolved
