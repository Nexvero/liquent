"""LQ-037 Phase 1 — Regressionstests für den bestehenden BacktestRunner.

Reine Tests gegen den vorhandenen Code (kein src-Änderung, keine neue Semantik).
Alle Fixtures sind synthetisch, in-memory, UTC-aware — keine CSV, kein File-I/O,
kein Netzwerk. Die Tests sichern den in LQ-035/LQ-036 dokumentierten Ist-Zustand
ab und erzwingen ausdrücklich KEINE Stop-Exit-/Order-/Position-Lifecycle-Semantik.

Verifizierte Schnittstellen (read-only, LQ-036):
- ``BacktestRunner(source, risk_engine, cost_model, seed=0, strategy=None,
  initial_equity=0.0, ...)`` mit ``run() -> BacktestResult``.
- ``source.market_data()`` liefert die Bars; ``strategy.generate_signals(bars)``
  die Signale.
- Default-``sizing_mode`` ist ``"absolute"`` (``reference_price`` ignoriert);
  ein ``RiskEngine()`` ohne konfigurierte Limits lehnt fail-safe ab.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Sequence

from liquent.backtesting.metrics import TradeResult
from liquent.backtesting.runner import BacktestResult, BacktestRunner, CostModel
from liquent.domain.models import Direction, MarketData, Signal
from liquent.risk.engine import RiskEngine, RiskLimits

_START = datetime(2026, 1, 1, tzinfo=timezone.utc)


# --------------------------------------------------------------------------- #
# Synthetische In-Memory-Fixtures (passend zu den echten Interfaces)
# --------------------------------------------------------------------------- #
def _bars(mids: Sequence[float], *, interval_minutes: int = 5) -> tuple[MarketData, ...]:
    """Deterministische, UTC-aware ``MarketData``-Sequenz aus einer Mid-Serie.

    ``bid == ask == mid`` (half_spread 0) — der Runner nutzt den Mid
    ``(bid + ask) / 2``.
    """
    return tuple(
        MarketData(
            timestamp=_START + timedelta(minutes=i * interval_minutes),
            bid=float(mid),
            ask=float(mid),
            volume=1.0,
        )
        for i, mid in enumerate(mids)
    )


class RecordingDataSource:
    """In-Memory-``DataSource``, die ``market_data()``-Aufrufe zählt."""

    def __init__(self, bars: Sequence[MarketData]) -> None:
        self._bars = tuple(bars)
        self.market_data_calls = 0

    def market_data(self) -> tuple[MarketData, ...]:
        self.market_data_calls += 1
        return self._bars

    def order_book_snapshots(self) -> tuple[object, ...]:
        return ()


class RecordingStrategy:
    """Strategie mit fester Signal-Liste, die ``generate_signals()`` zählt."""

    def __init__(self, signals: Sequence[Signal]) -> None:
        self._signals = tuple(signals)
        self.generate_signals_calls = 0

    def generate_signals(self, market_data: Sequence[MarketData]) -> tuple[Signal, ...]:
        self.generate_signals_calls += 1
        return self._signals


def _approving_limits() -> RiskLimits:
    """Absolute Limits, die ein gültiges Signal freigeben (size == risk_per_trade)."""
    return RiskLimits(
        max_position_size=1.0,
        max_total_exposure=100.0,
        risk_per_trade=1.0,
        max_daily_drawdown=1000.0,  # hoch -> Drawdown-Stopp stört die Tests nicht
    )


def _long_signal(bars: Sequence[MarketData], index: int = 0, **kw) -> Signal:
    return Signal(
        timestamp=bars[index].timestamp,
        direction=Direction.LONG,
        strength=1.0,
        **kw,
    )


# --------------------------------------------------------------------------- #
# 1 — Runner-Vertrag
# --------------------------------------------------------------------------- #
def test_runner_returns_backtest_result():
    source = RecordingDataSource(_bars([100.0, 110.0]))
    result = BacktestRunner(
        source, RiskEngine(_approving_limits()), CostModel(),
        strategy=RecordingStrategy([]),
    ).run()

    assert isinstance(result, BacktestResult)
    assert isinstance(result.trades, tuple)
    assert isinstance(result.metrics, dict)
    assert isinstance(result.equity_curve, tuple)
    assert isinstance(result.ending_equity, float)


# --------------------------------------------------------------------------- #
# 2 — DataSource.market_data() wird genutzt
# --------------------------------------------------------------------------- #
def test_runner_uses_data_source_market_data():
    source = RecordingDataSource(_bars([100.0, 110.0]))
    BacktestRunner(
        source, RiskEngine(_approving_limits()), CostModel(),
        strategy=RecordingStrategy([]),
    ).run()
    assert source.market_data_calls >= 1


# --------------------------------------------------------------------------- #
# 3 — Strategy.generate_signals() wird genutzt
# --------------------------------------------------------------------------- #
def test_runner_uses_strategy_generate_signals():
    source = RecordingDataSource(_bars([100.0, 110.0]))
    strategy = RecordingStrategy([])
    BacktestRunner(
        source, RiskEngine(_approving_limits()), CostModel(), strategy=strategy,
    ).run()
    assert strategy.generate_signals_calls == 1


# --------------------------------------------------------------------------- #
# 4 — Leere Signal-Liste -> deterministisches Ergebnis, keine Trades
# --------------------------------------------------------------------------- #
def test_empty_signals_produce_deterministic_result():
    def _run() -> BacktestResult:
        return BacktestRunner(
            RecordingDataSource(_bars([100.0, 101.0, 102.0])),
            RiskEngine(_approving_limits()),
            CostModel(),
            strategy=RecordingStrategy([]),
            initial_equity=1000.0,
        ).run()

    res_a, res_b = _run(), _run()
    assert res_a == res_b  # deterministisch (inkl. experiment_id)
    assert res_a.number_of_trades == 0
    assert res_a.trades == ()
    assert res_a.equity_curve == (1000.0,)
    assert res_a.ending_equity == 1000.0


# --------------------------------------------------------------------------- #
# 5 — Rejected Signal -> kein TradeResult
# --------------------------------------------------------------------------- #
def test_rejected_signal_does_not_create_trade():
    bars = _bars([100.0, 110.0])
    # RiskEngine() ohne konfigurierte Limits lehnt fail-safe ab (approved=False).
    result = BacktestRunner(
        RecordingDataSource(bars), RiskEngine(), CostModel(),
        strategy=RecordingStrategy([_long_signal(bars)]),
    ).run()

    assert result.number_of_trades == 0
    assert result.trades == ()
    assert result.approved_signals == 0
    assert result.rejected_signals == 1


# --------------------------------------------------------------------------- #
# 6 — Approved Signal -> deterministischer TradeResult (reale Felder)
# --------------------------------------------------------------------------- #
def test_approved_signal_creates_trade_result():
    bars = _bars([100.0, 110.0])
    result = BacktestRunner(
        RecordingDataSource(bars), RiskEngine(_approving_limits()), CostModel(),
        strategy=RecordingStrategy([_long_signal(bars)]),
    ).run()

    assert result.number_of_trades == 1
    assert result.approved_signals == 1
    (trade,) = result.trades
    assert isinstance(trade, TradeResult)

    # Reale Felder (LQ-036): side/entry_price/exit_price/quantity/entry_time/exit_time.
    assert trade.side == "long"
    assert trade.entry_price == 100.0
    assert trade.exit_price == 110.0
    assert trade.quantity == 1.0  # size == risk_per_trade (absolute Limits)
    assert trade.gross_pnl == (110.0 - 100.0) * 1.0
    assert isinstance(trade.entry_time, str)
    assert isinstance(trade.exit_time, str)
    assert trade.duration_bars == 1

    # KEINE erfundenen Felder: kein exit_reason, kein opened_at/closed_at.
    trade_fields = {f.name for f in dataclasses.fields(trade)}
    assert "exit_reason" not in trade_fields
    assert "opened_at" not in trade_fields
    assert "closed_at" not in trade_fields


# --------------------------------------------------------------------------- #
# 7 — CostModel verändert nur Kosten-/Nettofelder, nicht den Signalfluss
# --------------------------------------------------------------------------- #
def test_cost_model_changes_cost_or_net_fields_only():
    bars = _bars([100.0, 110.0])

    def _run(cost_model: CostModel) -> BacktestResult:
        return BacktestRunner(
            RecordingDataSource(bars), RiskEngine(_approving_limits()), cost_model,
            strategy=RecordingStrategy([_long_signal(bars)]),
        ).run()

    frictionless = _run(CostModel())
    with_costs = _run(CostModel(fee_rate=0.01))

    (free_trade,) = frictionless.trades
    (cost_trade,) = with_costs.trades

    # gross_pnl bleibt identisch; nur costs/net_pnl ändern sich.
    assert free_trade.gross_pnl == cost_trade.gross_pnl
    assert free_trade.costs == 0.0
    assert cost_trade.costs > 0.0
    assert cost_trade.net_pnl < free_trade.net_pnl
    assert cost_trade.net_pnl == cost_trade.gross_pnl - cost_trade.costs

    # Signalfluss unverändert: gleiche Anzahl approved/Trades.
    assert frictionless.approved_signals == with_costs.approved_signals == 1
    assert frictionless.number_of_trades == with_costs.number_of_trades == 1


# --------------------------------------------------------------------------- #
# 8 — BacktestResult exponiert keine Reporting-Metadaten
# --------------------------------------------------------------------------- #
def test_backtest_result_does_not_expose_reporting_metadata():
    result = BacktestRunner(
        RecordingDataSource(_bars([100.0, 110.0])),
        RiskEngine(_approving_limits()), CostModel(),
        strategy=RecordingStrategy([]),
    ).run()

    field_names = {f.name for f in dataclasses.fields(result)}
    # Diese Metadaten liegen im Reporting-Layer (BacktestExperimentSummary),
    # NICHT auf BacktestResult.
    assert "generated_at" not in field_names
    assert "strategy_metadata" not in field_names
    assert "cost_metadata" not in field_names


# --------------------------------------------------------------------------- #
# 9 — stop_price ist sizing-only und löst KEINEN Stop-Exit aus
# --------------------------------------------------------------------------- #
def test_stop_price_is_sizing_only_not_stop_exit():
    # Mid fällt unter den gesetzten stop_price; ein echter Stop-Exit würde am
    # Stop schließen. Der aktuelle Close-to-Close-Runner schließt jedoch zum
    # Folge-Bar-Mid (98.0) — stop_price wirkt nur im Sizing (hier absolute Mode,
    # daher ignoriert), nicht als Exit.
    bars = _bars([100.0, 98.0])
    signal = _long_signal(bars, stop_price=99.0)
    result = BacktestRunner(
        RecordingDataSource(bars), RiskEngine(_approving_limits()), CostModel(),
        strategy=RecordingStrategy([signal]),
    ).run()

    assert result.number_of_trades == 1
    (trade,) = result.trades
    assert trade.exit_price == 98.0  # Folge-Bar-Mid, NICHT der Stop (99.0)
    assert trade.duration_bars == 1
    assert "exit_reason" not in {f.name for f in dataclasses.fields(trade)}


# --------------------------------------------------------------------------- #
# 10 — Kein Order-/Position-Lifecycle-Objekt im Runner-Output
# --------------------------------------------------------------------------- #
def test_no_order_or_position_lifecycle_objects_created():
    bars = _bars([100.0, 110.0])
    result = BacktestRunner(
        RecordingDataSource(bars), RiskEngine(_approving_limits()), CostModel(),
        strategy=RecordingStrategy([_long_signal(bars)]),
    ).run()

    # Trades sind ausschließlich TradeResult — kein Order-/Position-Objekt.
    assert all(type(t).__name__ == "TradeResult" for t in result.trades)

    field_names = {f.name for f in dataclasses.fields(result)}
    for forbidden in ("orders", "positions", "position", "order"):
        assert forbidden not in field_names


# --------------------------------------------------------------------------- #
# 11 — Safety: die Regressionstest-Datei zieht keine Netz-/Exchange-Imports
# --------------------------------------------------------------------------- #
def test_regression_module_has_no_network_or_exchange_imports():
    source = Path(__file__).read_text(encoding="utf-8").lower()
    # Fragment-gebaut, damit diese Testdatei sich nicht selbst matcht.
    forbidden = ["import " + name for name in ("requests", "urllib", "socket", "ccxt")]
    for token in forbidden:
        assert token not in source, f"unerwarteter Import: {token!r}"
