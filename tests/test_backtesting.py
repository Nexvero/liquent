"""Backtesting-Metrik-Tests (LQ-005 Phase 1).

Spec: liquent/06_Backtesting/Backtesting_Framework_Spec.md

Deckt die reine Grundlage ab: TradeResult-Validierung, Kostenberechnung und die
Mindestmetriken inkl. ihrer Sonderfälle (leere Liste, keine Verlusttrades).
Bewusst KEINE Runner-/Daten-/Strategie-Tests (folgen in späteren Phasen).
"""

import math
from datetime import datetime, timezone
from pathlib import Path

from liquent.data.sources import DataSourceMetadata, Gap, HistoricalFileSource
from liquent.backtesting.metrics import (
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
from liquent.backtesting.runner import (
    BacktestResult,
    BacktestRunner,
    CostModel,
    MomentumStubStrategy,
)
from liquent.domain.models import Direction, MarketData, Signal
from liquent.risk.engine import RiskEngine, RiskLimits


def _trade(net_pnl: float, *, side: str = "long", r: float = 0.0, bars: int = 1) -> TradeResult:
    """Hilfsfunktion: minimaler TradeResult mit gesetztem net_pnl."""
    return TradeResult(
        entry_price=100.0,
        exit_price=100.0 + net_pnl,
        quantity=1.0,
        side=side,
        gross_pnl=net_pnl,
        costs=0.0,
        net_pnl=net_pnl,
        r_multiple=r,
        duration_bars=bars,
    )


# --------------------------------------------------------------------------- #
# 1–2: TradeResult-Validierung
# --------------------------------------------------------------------------- #
def test_trade_result_validates_side():
    ok = TradeResult(entry_price=100.0, exit_price=101.0, quantity=1.0, side="short")
    assert ok.side == "short"
    raised = False
    try:
        TradeResult(entry_price=100.0, exit_price=101.0, quantity=1.0, side="buy")
    except ValueError:
        raised = True
    assert raised, "ungültige side muss ValueError auslösen"


def test_trade_result_rejects_negative_quantity():
    raised = False
    try:
        TradeResult(entry_price=100.0, exit_price=101.0, quantity=-1.0, side="long")
    except ValueError:
        raised = True
    assert raised, "negative quantity muss ValueError auslösen"

    raised_bars = False
    try:
        TradeResult(
            entry_price=100.0, exit_price=101.0, quantity=1.0, side="long",
            duration_bars=-1,
        )
    except ValueError:
        raised_bars = True
    assert raised_bars, "negative duration_bars muss ValueError auslösen"


# --------------------------------------------------------------------------- #
# 3: Kostenberechnung
# --------------------------------------------------------------------------- #
def test_calculate_trade_costs_combines_fee_spread_slippage():
    cm = CostModel(fee_rate=0.001, spread=0.05, slippage=0.0005)
    # price=100, quantity=2 -> notional=200
    # fee     = 200 * 0.001  = 0.20
    # spread  = 2   * 0.05   = 0.10
    # slip    = 200 * 0.0005 = 0.10
    # total   = 0.40
    cost = calculate_trade_costs(100.0, 2.0, cm)
    assert math.isclose(cost, 0.40, rel_tol=1e-9)


def test_calculate_trade_costs_zero_model_is_free():
    assert calculate_trade_costs(100.0, 3.0, CostModel()) == 0.0


# --------------------------------------------------------------------------- #
# 4–12: Metriken
# --------------------------------------------------------------------------- #
def test_number_of_trades():
    assert number_of_trades([]) == 0
    assert number_of_trades([_trade(1.0), _trade(-1.0), _trade(2.0)]) == 3


def test_win_rate():
    assert win_rate([]) == 0.0
    trades = [_trade(1.0), _trade(-1.0), _trade(2.0), _trade(-0.5)]
    assert math.isclose(win_rate(trades), 0.5)


def test_profit_factor_normal_and_no_losers():
    trades = [_trade(4.0), _trade(-2.0)]
    assert math.isclose(profit_factor(trades), 2.0)
    # nur Gewinner -> inf
    assert profit_factor([_trade(1.0), _trade(3.0)]) == float("inf")
    # leer -> 0.0
    assert profit_factor([]) == 0.0
    # alles 0 -> 0.0 (kein Gewinn, kein Verlust)
    assert profit_factor([_trade(0.0)]) == 0.0


def test_max_drawdown():
    assert max_drawdown([]) == 0.0
    # Peak 120 -> Trough 90 = DD 30
    assert math.isclose(max_drawdown([100.0, 120.0, 90.0, 110.0]), 30.0)
    # monoton steigend -> 0
    assert max_drawdown([10.0, 20.0, 30.0]) == 0.0


def test_average_r_multiple():
    assert average_r_multiple([]) == 0.0
    trades = [_trade(1.0, r=2.0), _trade(-1.0, r=-1.0)]
    assert math.isclose(average_r_multiple(trades), 0.5)


def test_expectancy():
    assert expectancy([]) == 0.0
    trades = [_trade(3.0), _trade(-1.0), _trade(1.0)]
    assert math.isclose(expectancy(trades), 1.0)


def test_exposure_time():
    trades = [_trade(1.0, bars=2), _trade(-1.0, bars=1)]
    assert math.isclose(exposure_time(trades, total_bars=6), 0.5)
    # total_bars <= 0 -> 0.0
    assert exposure_time(trades, total_bars=0) == 0.0
    assert exposure_time([], total_bars=10) == 0.0


def test_worst_losing_streak():
    assert worst_losing_streak([]) == 0
    seq = [_trade(1.0), _trade(-1.0), _trade(-1.0), _trade(-1.0), _trade(2.0), _trade(-1.0)]
    assert worst_losing_streak(seq) == 3


def test_best_and_worst_trade():
    trades = [_trade(1.0), _trade(-2.0), _trade(3.5)]
    assert math.isclose(best_trade(trades), 3.5)
    assert math.isclose(worst_trade(trades), -2.0)


# --------------------------------------------------------------------------- #
# 13: leere Liste liefert überall sichere Defaults
# --------------------------------------------------------------------------- #
def test_empty_trade_list_safe_defaults():
    empty: list[TradeResult] = []
    assert number_of_trades(empty) == 0
    assert win_rate(empty) == 0.0
    assert profit_factor(empty) == 0.0
    assert max_drawdown([]) == 0.0
    assert average_r_multiple(empty) == 0.0
    assert expectancy(empty) == 0.0
    assert exposure_time(empty, total_bars=10) == 0.0
    assert worst_losing_streak(empty) == 0
    assert best_trade(empty) == 0.0
    assert worst_trade(empty) == 0.0


# --------------------------------------------------------------------------- #
# Phase 2: BacktestRunner (Close-to-Close, Long & Short, Risk-First)
# --------------------------------------------------------------------------- #
class _FakeSource:
    """Deterministische In-Memory-DataSource aus einer Mid-Preis-Liste.

    bid/ask werden symmetrisch um den Mid gelegt, sodass _mid() den Mid liefert.
    Keine Datei, kein Netzwerk.
    """

    def __init__(self, mids: list[float]) -> None:
        self._mids = mids

    def market_data(self):
        bars = []
        for i, m in enumerate(self._mids):
            bars.append(
                MarketData(
                    timestamp=datetime(2026, 6, 2, 0, i, tzinfo=timezone.utc),
                    bid=m - 0.5,
                    ask=m + 0.5,
                    volume=1.0,
                )
            )
        return bars

    def order_book_snapshots(self):
        return []


def _valid_limits() -> RiskLimits:
    return RiskLimits(
        max_position_size=10.0,
        max_total_exposure=100.0,
        risk_per_trade=5.0,
        max_daily_drawdown=1000.0,  # hoch, damit der Drawdown-Stopp Tests nicht stört
    )


def test_runner_returns_backtest_result_type():
    """run() liefert die standardisierte, immutable BacktestResult-Struktur."""
    result = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0]), RiskEngine(_valid_limits()), CostModel()
    ).run()
    assert isinstance(result, BacktestResult)
    assert isinstance(result.trades, tuple)
    assert isinstance(result.equity_curve, tuple)


# 1: Determinismus — gleicher Input -> identisches Ergebnis (inkl. ID).
def test_runner_deterministic_same_input_same_result():
    cm = CostModel(fee_rate=0.001, spread=0.05, slippage=0.0005)
    res_a = BacktestRunner(
        _FakeSource([100.0, 102.0, 101.0, 103.0]), RiskEngine(_valid_limits()), cm, seed=42
    ).run()
    res_b = BacktestRunner(
        _FakeSource([100.0, 102.0, 101.0, 103.0]), RiskEngine(_valid_limits()), cm, seed=42
    ).run()
    assert res_a == res_b
    assert res_a.experiment_id == res_b.experiment_id


# 2: Leere Daten -> sauberes Ergebnis, kein Crash.
def test_runner_empty_data_no_crash():
    res = BacktestRunner(_FakeSource([]), RiskEngine(_valid_limits()), CostModel()).run()
    assert res.number_of_trades == 0
    assert res.approved_signals == 0
    assert res.rejected_signals == 0
    assert res.trades == ()
    assert res.equity_curve == (res.starting_equity,)
    assert res.ending_equity == res.starting_equity
    assert res.metrics["number_of_trades"] == 0
    assert res.metrics["max_drawdown"] == 0.0
    assert res.parameters["bars"] == 0
    assert res.parameters["period_start"] == ""


# 3: Risk Engine lehnt ab -> kein Trade.
def test_runner_risk_reject_means_no_trade():
    """Default-Limits (alle 0) lehnen fail-safe ab -> Signale, aber keine Trades."""
    res = BacktestRunner(
        _FakeSource([100.0, 102.0, 101.0]), RiskEngine(), CostModel()
    ).run()  # Default-Limits -> reject
    assert res.parameters["signals_total"] > 0
    assert res.approved_signals == 0
    assert res.rejected_signals == res.parameters["signals_total"]
    assert res.number_of_trades == 0
    assert res.trades == ()
    assert res.ending_equity == res.starting_equity


# 4: Risk Engine erlaubt -> genau ein Trade im Stub-Szenario.
def test_runner_approve_yields_single_trade_stub():
    """[100,102,105]: nur i=1 erzeugt ein LONG-Signal -> genau ein Trade."""
    res = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0]), RiskEngine(_valid_limits()), CostModel()
    ).run()
    assert res.approved_signals == 1
    assert res.rejected_signals == 0
    assert res.number_of_trades == 1
    assert len(res.trades) == 1
    assert res.trades[0].side == "long"


# 5: Kostenmodell reduziert das Ergebnis.
def test_runner_costs_reduce_result():
    mids = [100.0, 102.0, 105.0]  # ein gewinnender LONG-Trade
    free = BacktestRunner(_FakeSource(mids), RiskEngine(_valid_limits()), CostModel()).run()
    costly = BacktestRunner(
        _FakeSource(mids),
        RiskEngine(_valid_limits()),
        CostModel(fee_rate=0.001, spread=0.05, slippage=0.0005),
    ).run()
    assert free.number_of_trades == 1
    assert costly.ending_equity < free.ending_equity
    assert free.parameters["frictionless"] is True
    assert costly.parameters["frictionless"] is False


# 6: Equity-Kurve beginnt mit starting_equity.
def test_runner_equity_curve_starts_with_starting_equity():
    start = 1000.0
    res = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0]),
        RiskEngine(_valid_limits()),
        CostModel(),
        initial_equity=start,
    ).run()
    assert res.starting_equity == start
    assert res.equity_curve[0] == start
    assert res.ending_equity == res.equity_curve[-1]


# 7: Metriken werden im Ergebnis befüllt.
def test_runner_metrics_populated():
    res = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0]),
        RiskEngine(_valid_limits()),
        CostModel(fee_rate=0.001, spread=0.05, slippage=0.0005),
        seed=7,
    ).run()
    for key in (
        "number_of_trades", "win_rate", "profit_factor", "max_drawdown",
        "average_r_multiple", "expectancy", "exposure_time",
        "worst_losing_streak", "best_trade", "worst_trade",
    ):
        assert key in res.metrics
    assert res.metrics["number_of_trades"] == res.number_of_trades


# 8: Rejected/approved Counts stimmen.
def test_runner_gate_counts_consistent():
    res = BacktestRunner(
        _FakeSource([100.0, 102.0, 101.0, 103.0, 99.0]),
        RiskEngine(_valid_limits()),
        CostModel(),
    ).run()
    assert res.approved_signals + res.rejected_signals == res.parameters["signals_total"]
    # Jedes freigegebene Signal erzeugt genau einen Trade (kein Bypass, keine Doppelung).
    assert res.approved_signals == res.number_of_trades


# 9: Result enthält (skalare) Parameter.
def test_runner_result_contains_parameters():
    res = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0]),
        RiskEngine(_valid_limits()),
        CostModel(fee_rate=0.001, spread=0.05, slippage=0.0005),
        seed=7,
    ).run()
    for key in (
        "seed", "direction_mode", "trade_simulation", "fee_rate", "spread",
        "slippage", "frictionless", "max_position_size", "max_total_exposure",
        "risk_per_trade", "max_daily_drawdown", "bars",
    ):
        assert key in res.parameters
    assert res.parameters["seed"] == 7
    # Parameter sind flach/skalar serialisierbar.
    for value in res.parameters.values():
        assert isinstance(value, (str, int, float, bool))
    assert res.experiment_id.startswith("lq005-")


# Zusatz: Long & Short im selben Lauf (deckt SHORT-Pfad ab).
def test_runner_long_and_short_trades():
    # i=1: 102>100 -> LONG (entry 102, exit 101 -> Verlust)
    # i=2: 101<102 -> SHORT (entry 101, exit 103 -> Verlust)
    res = BacktestRunner(
        _FakeSource([100.0, 102.0, 101.0, 103.0]), RiskEngine(_valid_limits()), CostModel()
    ).run()
    assert res.number_of_trades == 2
    assert [t.side for t in res.trades] == ["long", "short"]
    assert res.metrics["win_rate"] == 0.0
    assert res.metrics["worst_losing_streak"] == 2


# 10: Keine Netzwerk-/Live-/Paper-Trading-Pfade.
def test_runner_no_network_live_or_paper_paths():
    """Statische + dynamische Prüfung: kein I/O-, Live- oder Paper-Trading-Pfad."""
    import inspect

    from liquent.backtesting import runner as runner_module

    source_code = inspect.getsource(runner_module)
    # Echte I/O-/Netzwerk-/Live-Pfade dürfen nicht vorkommen.
    forbidden = (
        "socket", "urllib", "requests", "http://", "https://",
        "websocket", "ccxt", "live_order", "place_order",
    )
    for token in forbidden:
        assert token not in source_code, f"runner darf {token!r} nicht referenzieren"
    # Der Runner bindet das Paper-Trading-Modul nicht ein (kein Bot-Import).
    assert "bot.paper_trading" not in source_code
    assert "import paper_trading" not in source_code

    res = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0]), RiskEngine(_valid_limits()), CostModel()
    ).run()
    assert res.parameters["mode"] == "analysis"
    assert res.parameters["live_execution"] is False
    assert res.parameters["network_calls"] is False
    assert res.parameters["paper_trading"] is False


# --------------------------------------------------------------------------- #
# Phase 3: HistoricalFileSource (lokaler OHLCV-CSV-Lader + Datenvalidierung)
# --------------------------------------------------------------------------- #
_FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return str(_FIXTURES / name)


def _assert_value_error(path: str) -> None:
    """Hilfsfunktion: market_data() für die Fixture muss ValueError werfen."""
    raised = False
    try:
        HistoricalFileSource(path).market_data()
    except ValueError:
        raised = True
    assert raised, f"{path}: erwartete ValueError wurde nicht ausgelöst"


# 1 + 2: gültige CSV wird geladen, alle Pflichtfelder gelesen.
def test_csv_loads_valid_file_with_all_fields():
    bars = HistoricalFileSource(_fixture("ohlcv_valid.csv")).market_data()
    assert len(bars) == 3
    first = bars[0]
    assert first.timestamp == datetime(2026, 6, 2, 0, 0, tzinfo=timezone.utc)
    # close wird als Referenzpreis übernommen (bid = ask = close).
    assert first.bid == 100.5
    assert first.ask == 100.5
    assert first.volume == 1000.0


# 3: numerische Felder werden zu float.
def test_csv_numeric_fields_are_float():
    bars = HistoricalFileSource(_fixture("ohlcv_valid.csv")).market_data()
    for bar in bars:
        assert isinstance(bar.bid, float)
        assert isinstance(bar.ask, float)
        assert isinstance(bar.volume, float)


# 4: unsortierte Daten werden abgelehnt.
def test_csv_rejects_unsorted():
    _assert_value_error(_fixture("ohlcv_unsorted.csv"))


# 5: doppelte Zeitstempel werden abgelehnt.
def test_csv_rejects_duplicate_timestamp():
    _assert_value_error(_fixture("ohlcv_duplicate_timestamp.csv"))


# 6: negative Preise werden abgelehnt.
def test_csv_rejects_negative_price():
    _assert_value_error(_fixture("ohlcv_invalid_price.csv"))


# 7: negatives Volumen wird abgelehnt.
def test_csv_rejects_negative_volume():
    _assert_value_error(_fixture("ohlcv_negative_volume.csv"))


# 8: high < low wird abgelehnt.
def test_csv_rejects_high_less_than_low():
    _assert_value_error(_fixture("ohlcv_high_lt_low.csv"))


# 9: open außerhalb [low, high] wird abgelehnt.
def test_csv_rejects_open_out_of_range():
    _assert_value_error(_fixture("ohlcv_open_out_of_range.csv"))


# 10: close außerhalb [low, high] wird abgelehnt.
def test_csv_rejects_close_out_of_range():
    _assert_value_error(_fixture("ohlcv_close_out_of_range.csv"))


# 11: leere Datei / nur Kopfzeile wird stabil behandelt (leere Liste).
def test_csv_header_only_returns_empty_list():
    bars = HistoricalFileSource(_fixture("ohlcv_empty.csv")).market_data()
    assert bars == []


# 12: fehlende Pflichtspalte wird abgelehnt.
def test_csv_rejects_missing_required_column():
    _assert_value_error(_fixture("ohlcv_missing_column.csv"))


# Zusatz: leerer Zeitstempel wird abgelehnt.
def test_csv_rejects_empty_timestamp():
    _assert_value_error(_fixture("ohlcv_empty_timestamp.csv"))


# Zusatz: order_book_snapshots ist im OHLCV-Scope nicht implementiert.
def test_csv_order_book_snapshots_not_implemented():
    raised = False
    try:
        HistoricalFileSource(_fixture("ohlcv_valid.csv")).order_book_snapshots()
    except NotImplementedError:
        raised = True
    assert raised


# 13: Runner läuft mit geladener gültiger CSV (End-to-End, Risk-First).
def test_runner_runs_with_loaded_csv():
    source = HistoricalFileSource(_fixture("ohlcv_valid.csv"))
    result = BacktestRunner(
        source, RiskEngine(_valid_limits()), CostModel(), initial_equity=1000.0
    ).run()
    assert isinstance(result, BacktestResult)
    # close-Serie [100.5, 101.5, 102.0] steigt -> ein LONG-Signal (i=1).
    assert result.parameters["bars"] == 3
    assert result.number_of_trades == 1
    assert result.approved_signals == 1
    assert result.trades[0].side == "long"
    assert result.equity_curve[0] == 1000.0


def test_runner_runs_with_empty_csv():
    """Leere CSV -> Runner bleibt stabil, kein Trade, kein Crash."""
    source = HistoricalFileSource(_fixture("ohlcv_empty.csv"))
    result = BacktestRunner(source, RiskEngine(_valid_limits()), CostModel()).run()
    assert result.number_of_trades == 0
    assert result.parameters["bars"] == 0


# --------------------------------------------------------------------------- #
# Phase 4: injizierbare Strategie-Schnittstelle (nur Pipeline-Prüfung)
# --------------------------------------------------------------------------- #
# Einfache Fake-Strategien — ausschließlich Testcode, KEINE echte Handelslogik,
# keine Bewertung/Optimierung. Sie prüfen nur die technische Einsteckbarkeit.


class NoSignalStrategy:
    def generate_signals(self, market_data):
        return []


class AlwaysLongStrategy:
    """Long auf jedem ausführbaren Bar (Entry-Index 0..n-2)."""

    def generate_signals(self, market_data):
        bars = list(market_data)
        return [
            Signal(timestamp=bars[i].timestamp, direction=Direction.LONG, strength=1.0)
            for i in range(len(bars) - 1)
        ]


class SingleLongStrategy:
    """Genau ein Long-Signal am ersten Bar (falls ein Folge-Bar existiert)."""

    def generate_signals(self, market_data):
        bars = list(market_data)
        if len(bars) < 2:
            return []
        return [Signal(timestamp=bars[0].timestamp, direction=Direction.LONG, strength=1.0)]


class SingleShortStrategy:
    """Genau ein Short-Signal am ersten Bar (falls ein Folge-Bar existiert)."""

    def generate_signals(self, market_data):
        bars = list(market_data)
        if len(bars) < 2:
            return []
        return [Signal(timestamp=bars[0].timestamp, direction=Direction.SHORT, strength=1.0)]


class TwoSignalStrategy:
    """Zwei Signale: Long am Bar 0, Short am Bar 1 (braucht >= 3 Bars)."""

    def generate_signals(self, market_data):
        bars = list(market_data)
        out = []
        if len(bars) >= 2:
            out.append(Signal(timestamp=bars[0].timestamp, direction=Direction.LONG, strength=1.0))
        if len(bars) >= 3:
            out.append(Signal(timestamp=bars[1].timestamp, direction=Direction.SHORT, strength=1.0))
        return out


class RejectableSignalStrategy:
    """Ein valides Signal; mit Default-Limits lehnt die Risk Engine fail-safe ab."""

    def generate_signals(self, market_data):
        bars = list(market_data)
        if len(bars) < 2:
            return []
        return [Signal(timestamp=bars[0].timestamp, direction=Direction.LONG, strength=1.0)]


class LastBarOnlyStrategy:
    """Signal nur auf dem letzten Bar -> in Close-to-Close nicht ausführbar."""

    def generate_signals(self, market_data):
        bars = list(market_data)
        if not bars:
            return []
        return [Signal(timestamp=bars[-1].timestamp, direction=Direction.LONG, strength=1.0)]


class InvalidSignalStrategy:
    """Liefert ein ungültiges Objekt (kein Signal) -> fail-safe Exception."""

    def generate_signals(self, market_data):
        return ["not-a-signal"]


class UnknownTimestampStrategy:
    """Signal mit Zeitstempel, der nicht in den Daten vorkommt -> Exception."""

    def generate_signals(self, market_data):
        return [
            Signal(
                timestamp=datetime(1999, 1, 1, tzinfo=timezone.utc),
                direction=Direction.LONG,
                strength=1.0,
            )
        ]


# 1: Ohne Strategie nutzt der Runner den bisherigen Default-Stub.
def test_default_strategy_is_momentum_stub():
    runner = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0]), RiskEngine(_valid_limits()), CostModel()
    )
    assert isinstance(runner.strategy, MomentumStubStrategy)
    res = runner.run()
    assert res.parameters["strategy"] == "MomentumStubStrategy"
    # Default-Lauf == explizit injizierter Momentum-Stub (identisches Ergebnis).
    res_explicit = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0]),
        RiskEngine(_valid_limits()),
        CostModel(),
        strategy=MomentumStubStrategy(),
    ).run()
    assert res == res_explicit


# 2: Custom Strategy ohne Signal -> keine Trades, stabiles Ergebnis.
def test_custom_strategy_no_signal_no_trades():
    res = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0]),
        RiskEngine(_valid_limits()),
        CostModel(),
        strategy=NoSignalStrategy(),
    ).run()
    assert res.parameters["signals_total"] == 0
    assert res.approved_signals == 0
    assert res.rejected_signals == 0
    assert res.number_of_trades == 0
    assert res.trades == ()
    assert res.ending_equity == res.starting_equity
    assert res.parameters["strategy"] == "NoSignalStrategy"


# 3: Custom Strategy mit einem Signal -> genau ein Risk-Gate-Durchlauf.
def test_custom_strategy_single_signal_one_gate_pass():
    res = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0]),
        RiskEngine(_valid_limits()),
        CostModel(),
        strategy=SingleLongStrategy(),
    ).run()
    assert res.parameters["signals_total"] == 1
    assert res.approved_signals + res.rejected_signals == 1
    assert res.approved_signals == 1
    assert res.number_of_trades == 1


# 4: Custom Strategy mit zwei Signalen -> Counts stimmen.
def test_custom_strategy_two_signals_counts():
    res = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0]),
        RiskEngine(_valid_limits()),
        CostModel(),
        strategy=TwoSignalStrategy(),
    ).run()
    assert res.parameters["signals_total"] == 2
    assert res.approved_signals == 2
    assert res.rejected_signals == 0
    assert res.number_of_trades == 2
    assert res.approved_signals + res.rejected_signals == res.parameters["signals_total"]


# 5: Risk Engine lehnt Custom-Strategy-Signal ab -> kein Trade.
def test_custom_strategy_rejected_means_no_trade():
    res = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0]),
        RiskEngine(),  # Default-Limits -> fail-safe reject
        CostModel(),
        strategy=RejectableSignalStrategy(),
    ).run()
    assert res.parameters["signals_total"] == 1
    assert res.approved_signals == 0
    assert res.rejected_signals == 1
    assert res.number_of_trades == 0
    assert res.trades == ()


# 6: Custom Strategy kann ein Long-Signal erzeugen.
def test_custom_strategy_can_emit_long():
    res = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0]),
        RiskEngine(_valid_limits()),
        CostModel(),
        strategy=SingleLongStrategy(),
    ).run()
    assert res.number_of_trades == 1
    assert res.trades[0].side == "long"


# 7: Custom Strategy kann ein Short-Signal erzeugen.
def test_custom_strategy_can_emit_short():
    res = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0]),
        RiskEngine(_valid_limits()),
        CostModel(),
        strategy=SingleShortStrategy(),
    ).run()
    assert res.number_of_trades == 1
    assert res.trades[0].side == "short"


# 9: Strategie-Ergebnis ist deterministisch.
def test_custom_strategy_deterministic():
    res_a = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0, 103.0]),
        RiskEngine(_valid_limits()),
        CostModel(),
        strategy=AlwaysLongStrategy(),
        seed=5,
    ).run()
    res_b = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0, 103.0]),
        RiskEngine(_valid_limits()),
        CostModel(),
        strategy=AlwaysLongStrategy(),
        seed=5,
    ).run()
    assert res_a == res_b
    assert res_a.experiment_id == res_b.experiment_id


# 10: Ungültige Signal-Objekte -> fail-safe mit klarer Exception.
def test_custom_strategy_invalid_signal_raises():
    runner = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0]),
        RiskEngine(_valid_limits()),
        CostModel(),
        strategy=InvalidSignalStrategy(),
    )
    raised = False
    try:
        runner.run()
    except (TypeError, ValueError):
        raised = True
    assert raised, "ungültiges Signal-Objekt muss fail-safe eine Exception auslösen"


# 10b: Signal-Zeitstempel außerhalb der Daten -> klare Exception.
def test_custom_strategy_unknown_timestamp_raises():
    runner = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0]),
        RiskEngine(_valid_limits()),
        CostModel(),
        strategy=UnknownTimestampStrategy(),
    )
    raised = False
    try:
        runner.run()
    except ValueError:
        raised = True
    assert raised


# Zusatz: Signal auf dem letzten Bar ist nicht ausführbar (dokumentiert verworfen).
def test_custom_strategy_last_bar_signal_not_executable():
    res = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0]),
        RiskEngine(_valid_limits()),
        CostModel(),
        strategy=LastBarOnlyStrategy(),
    ).run()
    assert res.parameters["signals_total"] == 0
    assert res.number_of_trades == 0


# Zusatz: Risk-First bleibt auch bei Custom-Strategy gewahrt (jedes Signal ans Gate).
def test_custom_strategy_risk_first_all_signals_gated():
    res = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0, 103.0]),
        RiskEngine(_valid_limits()),
        CostModel(),
        strategy=AlwaysLongStrategy(),
    ).run()
    # AlwaysLong erzeugt n-1 ausführbare Signale; alle laufen durchs Gate.
    assert res.parameters["signals_total"] == 3
    assert res.approved_signals + res.rejected_signals == 3
    assert res.number_of_trades == res.approved_signals


# --------------------------------------------------------------------------- #
# LQ-004 Phase 3: Runner übergibt reference_price (percent_risk lauffähig)
# --------------------------------------------------------------------------- #
# Test-Strategien mit Stop — nur Pipeline-Prüfung, KEINE echte Strategie.
class PercentRiskLongStrategy:
    """Ein Long-Signal am ersten Bar mit Stop (Default 95.0)."""

    def __init__(self, stop_price: float = 95.0):
        self._stop = stop_price

    def generate_signals(self, market_data):
        bars = list(market_data)
        if len(bars) < 2:
            return ()
        return (
            Signal(
                timestamp=bars[0].timestamp,
                direction=Direction.LONG,
                strength=1.0,
                stop_price=self._stop,
            ),
        )


class PercentRiskNoStopStrategy:
    """Ein Long-Signal am ersten Bar OHNE Stop (stop_price=None)."""

    def generate_signals(self, market_data):
        bars = list(market_data)
        if len(bars) < 2:
            return ()
        return (
            Signal(timestamp=bars[0].timestamp, direction=Direction.LONG, strength=1.0),
        )


def _pct_limits(**overrides) -> RiskLimits:
    """Valide percent_risk-Limits (großzügig, damit keine Caps stören)."""
    base = dict(
        max_position_size=1000.0,
        max_total_exposure=1_000_000.0,
        risk_per_trade=0.0,  # im percent_risk-Modus irrelevant
        max_daily_drawdown=1000.0,
        risk_per_trade_pct=0.01,
        max_position_notional=0.0,
        max_daily_loss=0.0,
        max_losing_streak=0,
        sizing_mode="percent_risk",
    )
    base.update(overrides)
    return RiskLimits(**base)


# 1: Bestehendes absolute-Mode-Verhalten bleibt unverändert.
def test_runner_absolute_mode_unchanged():
    res = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0]), RiskEngine(_valid_limits()), CostModel()
    ).run()
    assert res.parameters["strategy"] == "MomentumStubStrategy"
    assert res.number_of_trades == 1
    assert res.approved_signals == 1
    assert res.rejected_signals == 0
    assert res.trades[0].side == "long"


# 2 + 9: Runner übergibt reference_price -> percent_risk lehnt NICHT wegen
#        fehlendem reference_price ab; approved_signals korrekt.
def test_runner_percent_risk_passes_reference_price():
    res = BacktestRunner(
        _FakeSource([100.0, 110.0]),
        RiskEngine(_pct_limits()),
        CostModel(),
        strategy=PercentRiskLongStrategy(),
        initial_equity=10_000.0,
    ).run()
    assert res.parameters["signals_total"] == 1
    assert res.approved_signals == 1
    assert res.rejected_signals == 0


# 3: percent_risk Long-Backtest erzeugt genau einen Trade.
def test_runner_percent_risk_single_trade():
    res = BacktestRunner(
        _FakeSource([100.0, 110.0]),
        RiskEngine(_pct_limits()),
        CostModel(),
        strategy=PercentRiskLongStrategy(),
        initial_equity=10_000.0,
    ).run()
    assert res.number_of_trades == 1
    assert res.trades[0].side == "long"


# 4: percent_risk Long-Backtest nutzt die erwartete size (=20).
def test_runner_percent_risk_uses_expected_size():
    res = BacktestRunner(
        _FakeSource([100.0, 110.0]),
        RiskEngine(_pct_limits()),
        CostModel(),
        strategy=PercentRiskLongStrategy(),
        initial_equity=10_000.0,
    ).run()
    # equity 10_000 * 0.01 = 100 risk; stop_distance |100-95| = 5 -> size 20.
    assert res.trades[0].quantity == 20.0


# 5: percent_risk PnL nutzt die neue size korrekt (kostenfrei -> 200).
def test_runner_percent_risk_pnl_uses_size():
    res = BacktestRunner(
        _FakeSource([100.0, 110.0]),
        RiskEngine(_pct_limits()),
        CostModel(),  # frictionless
        strategy=PercentRiskLongStrategy(),
        initial_equity=10_000.0,
    ).run()
    # gross = (110 - 100) * 20 = 200; ohne Kosten -> net = 200.
    assert res.trades[0].gross_pnl == 200.0
    assert res.trades[0].net_pnl == 200.0
    assert res.ending_equity == 10_200.0


# 6: percent_risk Signal ohne stop_price -> abgelehnt, kein Trade.
def test_runner_percent_risk_missing_stop_no_trade():
    res = BacktestRunner(
        _FakeSource([100.0, 110.0]),
        RiskEngine(_pct_limits()),
        CostModel(),
        strategy=PercentRiskNoStopStrategy(),
        initial_equity=10_000.0,
    ).run()
    assert res.parameters["signals_total"] == 1
    assert res.approved_signals == 0
    assert res.rejected_signals == 1
    assert res.number_of_trades == 0
    assert res.trades == ()


# 7: percent_risk Long-Stop auf falscher Seite (>= Entry) -> abgelehnt, kein Trade.
def test_runner_percent_risk_wrong_side_stop_no_trade():
    res = BacktestRunner(
        _FakeSource([100.0, 110.0]),
        RiskEngine(_pct_limits()),
        CostModel(),
        strategy=PercentRiskLongStrategy(stop_price=105.0),  # über Entry 100
        initial_equity=10_000.0,
    ).run()
    assert res.approved_signals == 0
    assert res.rejected_signals == 1
    assert res.number_of_trades == 0


# 8: rejected/approved Counts bleiben konsistent zur Signalzahl.
def test_runner_percent_risk_gate_counts_consistent():
    res = BacktestRunner(
        _FakeSource([100.0, 110.0]),
        RiskEngine(_pct_limits()),
        CostModel(),
        strategy=PercentRiskLongStrategy(),
        initial_equity=10_000.0,
    ).run()
    assert res.approved_signals + res.rejected_signals == res.parameters["signals_total"]
    assert res.approved_signals == res.number_of_trades


# --------------------------------------------------------------------------- #
# LQ-004 Phase 4: erweiterte percent_risk Test-Matrix (Runner-Ebene)
# --------------------------------------------------------------------------- #
class PercentRiskShortStrategy:
    """Ein Short-Signal am ersten Bar mit Stop über Entry (Default 105.0)."""

    def __init__(self, stop_price: float = 105.0):
        self._stop = stop_price

    def generate_signals(self, market_data):
        bars = list(market_data)
        if len(bars) < 2:
            return ()
        return (
            Signal(
                timestamp=bars[0].timestamp,
                direction=Direction.SHORT,
                strength=1.0,
                stop_price=self._stop,
            ),
        )


class PercentRiskTwoLongStrategy:
    """Long-Signale an Bar 0 und Bar 1, jeweils mit Stop knapp unter Entry.

    Dient nur dazu, im Runner einen Folge-Drawdown-Stopp zu prüfen.
    """

    def generate_signals(self, market_data):
        bars = list(market_data)
        out = []
        if len(bars) >= 2:
            out.append(
                Signal(timestamp=bars[0].timestamp, direction=Direction.LONG, strength=1.0, stop_price=95.0)
            )
        if len(bars) >= 3:
            out.append(
                Signal(timestamp=bars[1].timestamp, direction=Direction.LONG, strength=1.0, stop_price=85.0)
            )
        return tuple(out)


# 1: Long, kostenlos -> erwartete size/PnL.
def test_runner_pct_long_no_cost_size_and_pnl():
    res = BacktestRunner(
        _FakeSource([100.0, 110.0]),
        RiskEngine(_pct_limits()),
        CostModel(),
        strategy=PercentRiskLongStrategy(),
        initial_equity=10_000.0,
    ).run()
    assert res.trades[0].quantity == 20.0
    assert res.trades[0].net_pnl == 200.0
    assert res.ending_equity == 10_200.0


# 2: Short, kostenlos -> erwartete size/PnL.
def test_runner_pct_short_no_cost_size_and_pnl():
    res = BacktestRunner(
        _FakeSource([100.0, 90.0]),
        RiskEngine(_pct_limits()),
        CostModel(),
        strategy=PercentRiskShortStrategy(),
        initial_equity=10_000.0,
    ).run()
    assert res.number_of_trades == 1
    assert res.trades[0].side == "short"
    assert res.trades[0].quantity == 20.0
    # short gross = (entry 100 - exit 90) * 20 = 200
    assert res.trades[0].net_pnl == 200.0
    assert res.ending_equity == 10_200.0


# 3: Kostenmodell reduziert net_pnl gegenüber frictionless.
def test_runner_pct_costs_reduce_net_pnl():
    free = BacktestRunner(
        _FakeSource([100.0, 110.0]),
        RiskEngine(_pct_limits()),
        CostModel(),
        strategy=PercentRiskLongStrategy(),
        initial_equity=10_000.0,
    ).run()
    costly = BacktestRunner(
        _FakeSource([100.0, 110.0]),
        RiskEngine(_pct_limits()),
        CostModel(fee_rate=0.001, spread=0.05, slippage=0.0005),
        strategy=PercentRiskLongStrategy(),
        initial_equity=10_000.0,
    ).run()
    assert free.number_of_trades == 1
    assert costly.number_of_trades == 1
    assert costly.trades[0].net_pnl < free.trades[0].net_pnl
    assert costly.trades[0].costs > 0.0


# 4: max_position_size kappt size im Runner.
def test_runner_pct_capped_by_max_position_size():
    res = BacktestRunner(
        _FakeSource([100.0, 110.0]),
        RiskEngine(_pct_limits(max_position_size=10.0)),
        CostModel(),
        strategy=PercentRiskLongStrategy(),
        initial_equity=10_000.0,
    ).run()
    assert res.trades[0].quantity == 10.0


# 5: max_position_notional kappt size im Runner.
def test_runner_pct_capped_by_max_notional():
    res = BacktestRunner(
        _FakeSource([100.0, 110.0]),
        RiskEngine(_pct_limits(max_position_notional=500.0)),
        CostModel(),
        strategy=PercentRiskLongStrategy(),
        initial_equity=10_000.0,
    ).run()
    assert res.trades[0].quantity == 5.0  # 500 / 100


# 6: verbleibendes max_total_exposure kappt size im Runner.
def test_runner_pct_capped_by_total_exposure():
    res = BacktestRunner(
        _FakeSource([100.0, 110.0]),
        RiskEngine(_pct_limits(max_total_exposure=300.0)),
        CostModel(),
        strategy=PercentRiskLongStrategy(),
        initial_equity=10_000.0,
    ).run()
    assert res.trades[0].quantity == 3.0  # 300 / 100


# 7: daily_drawdown blockiert ein Folge-Signal im Runner.
def test_runner_pct_daily_drawdown_blocks_followup():
    res = BacktestRunner(
        _FakeSource([100.0, 90.0, 95.0]),
        RiskEngine(_pct_limits(max_daily_drawdown=100.0)),
        CostModel(),
        strategy=PercentRiskTwoLongStrategy(),
        initial_equity=10_000.0,
    ).run()
    # Signal 0 (Verlust) freigegeben; Signal 1 wegen Drawdown-Stopp abgelehnt.
    assert res.parameters["signals_total"] == 2
    assert res.approved_signals == 1
    assert res.rejected_signals == 1
    assert res.number_of_trades == 1


# 8: fehlender Stop -> rejected, kein Trade.
def test_runner_pct_missing_stop_rejected():
    res = BacktestRunner(
        _FakeSource([100.0, 110.0]),
        RiskEngine(_pct_limits()),
        CostModel(),
        strategy=PercentRiskNoStopStrategy(),
        initial_equity=10_000.0,
    ).run()
    assert res.approved_signals == 0
    assert res.rejected_signals == 1
    assert res.number_of_trades == 0


# 9: Stop auf falscher Seite -> rejected, kein Trade.
def test_runner_pct_wrong_side_stop_rejected():
    res = BacktestRunner(
        _FakeSource([100.0, 110.0]),
        RiskEngine(_pct_limits()),
        CostModel(),
        strategy=PercentRiskLongStrategy(stop_price=105.0),  # über Entry 100
        initial_equity=10_000.0,
    ).run()
    assert res.approved_signals == 0
    assert res.rejected_signals == 1
    assert res.number_of_trades == 0


# 10: absolute-Modus bleibt unverändert (kein percent_risk-Pfad).
def test_runner_absolute_mode_still_default_behavior():
    res = BacktestRunner(
        _FakeSource([100.0, 102.0, 101.0, 103.0]),
        RiskEngine(_valid_limits()),
        CostModel(),
    ).run()
    assert res.parameters["sizing_mode"] == "absolute"
    assert res.number_of_trades == 2  # wie vor LQ-004 (Momentum-Stub)


# 11: Default MomentumStubStrategy im percent_risk-Modus -> kein Trade (kein Stop).
def test_runner_pct_default_stub_without_stop_no_trade():
    res = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0]),
        RiskEngine(_pct_limits()),
        CostModel(),
        # KEINE Strategie -> MomentumStubStrategy (ohne stop_price).
        initial_equity=10_000.0,
    ).run()
    assert res.parameters["strategy"] == "MomentumStubStrategy"
    assert res.number_of_trades == 0
    assert res.rejected_signals > 0


# 12: Teststrategie mit Stop erzeugt im percent_risk-Modus genau einen Trade.
def test_runner_pct_stop_strategy_creates_trade():
    res = BacktestRunner(
        _FakeSource([100.0, 110.0]),
        RiskEngine(_pct_limits()),
        CostModel(),
        strategy=PercentRiskLongStrategy(),
        initial_equity=10_000.0,
    ).run()
    assert res.number_of_trades == 1
    assert res.approved_signals == 1


# Runner-Parameter: percent_risk-Limits erscheinen in den (skalaren) Parametern.
def test_runner_parameters_expose_risk_sizing_fields():
    res = BacktestRunner(
        _FakeSource([100.0, 110.0]),
        RiskEngine(_pct_limits(max_position_notional=500.0)),
        CostModel(),
        strategy=PercentRiskLongStrategy(),
        initial_equity=10_000.0,
    ).run()
    for key in (
        "sizing_mode", "risk_per_trade_pct", "max_position_notional",
        "max_daily_loss", "max_losing_streak",
    ):
        assert key in res.parameters
    assert res.parameters["sizing_mode"] == "percent_risk"
    assert res.parameters["risk_per_trade_pct"] == 0.01
    assert res.parameters["max_position_notional"] == 500.0
    # Weiterhin nur skalare Parameter.
    for value in res.parameters.values():
        assert isinstance(value, (str, int, float, bool))


# --------------------------------------------------------------------------- #
# LQ-003 Phase 2: Gap-Erkennung + Timeframe-Parameter (HistoricalFileSource)
# --------------------------------------------------------------------------- #
def _expect_value_error(fn) -> None:
    raised = False
    try:
        fn()
    except ValueError:
        raised = True
    assert raised, "erwartete ValueError wurde nicht ausgelöst"


# 1: timeframe=None behält bisheriges Verhalten (keine Gap-Erkennung).
def test_csv_timeframe_none_keeps_behavior():
    src = HistoricalFileSource(_fixture("ohlcv_valid.csv"))
    bars = src.market_data()
    assert len(bars) == 3
    assert src.gap_report() == ()


# 2: timeframe="5m" ohne Gap lädt erfolgreich.
def test_csv_5m_no_gap_loads():
    src = HistoricalFileSource(_fixture("ohlcv_no_gap_5m.csv"), timeframe="5m")
    bars = src.market_data()
    assert len(bars) == 3
    assert src.gap_report() == ()


# 3: timeframe="1h" ohne Gap lädt erfolgreich.
def test_csv_1h_no_gap_loads():
    src = HistoricalFileSource(_fixture("ohlcv_no_gap_1h.csv"), timeframe="1h")
    bars = src.market_data()
    assert len(bars) == 3
    assert src.gap_report() == ()


# 4: unbekannter Timeframe -> ValueError (bei Konstruktion).
def test_csv_unknown_timeframe_rejected():
    _expect_value_error(lambda: HistoricalFileSource(_fixture("ohlcv_no_gap_5m.csv"), timeframe="3m"))


# 5: unbekannte gap_policy -> ValueError (bei Konstruktion).
def test_csv_unknown_gap_policy_rejected():
    _expect_value_error(
        lambda: HistoricalFileSource(
            _fixture("ohlcv_no_gap_5m.csv"), timeframe="5m", gap_policy="skip"
        )
    )


# 6: gap_policy="reject" wirft bei Gap.
def test_csv_reject_raises_on_gap():
    src = HistoricalFileSource(_fixture("ohlcv_gap_5m.csv"), timeframe="5m")  # reject default
    _expect_value_error(src.market_data)


# 7: Fehlermeldung bei Gap enthält previous/current/expected/actual.
def test_csv_reject_error_message_details():
    src = HistoricalFileSource(_fixture("ohlcv_gap_5m.csv"), timeframe="5m")
    message = ""
    try:
        src.market_data()
    except ValueError as exc:
        message = str(exc)
    assert "previous=" in message
    assert "current=" in message
    assert "expected_delta=300s" in message
    assert "actual_delta=600s" in message


# 8: gap_policy="flag" lädt trotz Gap.
def test_csv_flag_loads_despite_gap():
    src = HistoricalFileSource(_fixture("ohlcv_gap_5m.csv"), timeframe="5m", gap_policy="flag")
    bars = src.market_data()
    assert len(bars) == 3


# 9: gap_policy="flag" stellt einen Gap-Report bereit.
def test_csv_flag_provides_gap_report():
    src = HistoricalFileSource(_fixture("ohlcv_gap_5m.csv"), timeframe="5m", gap_policy="flag")
    src.market_data()
    gaps = src.gap_report()
    assert len(gaps) == 1
    assert isinstance(gaps[0], Gap)


# 10: gap_policy="tolerate", max_gaps=1 lädt bei einem Gap.
def test_csv_tolerate_within_max_gaps_loads():
    src = HistoricalFileSource(
        _fixture("ohlcv_gap_5m.csv"), timeframe="5m", gap_policy="tolerate", max_gaps=1
    )
    bars = src.market_data()
    assert len(bars) == 3
    assert len(src.gap_report()) == 1


# 11: gap_policy="tolerate", max_gaps=0 wirft bei einem Gap.
def test_csv_tolerate_exceeds_max_gaps_raises():
    src = HistoricalFileSource(
        _fixture("ohlcv_gap_5m.csv"), timeframe="5m", gap_policy="tolerate", max_gaps=0
    )
    _expect_value_error(src.market_data)


# 12: missing_bars wird korrekt berechnet (exaktes Vielfaches).
def test_csv_gap_missing_bars_computed():
    src = HistoricalFileSource(_fixture("ohlcv_gap_5m.csv"), timeframe="5m", gap_policy="flag")
    src.market_data()
    gap = src.gap_report()[0]
    assert gap.expected_delta_seconds == 300
    assert gap.actual_delta_seconds == 600
    assert gap.missing_bars == 1


# Zusatz: nicht-exaktes Vielfaches wird ebenfalls als Gap behandelt (deterministisch).
def test_csv_non_multiple_gap_is_flagged():
    src = HistoricalFileSource(
        _fixture("ohlcv_gap_non_multiple.csv"), timeframe="5m", gap_policy="flag"
    )
    src.market_data()
    gaps = src.gap_report()
    assert len(gaps) == 1
    assert gaps[0].expected_delta_seconds == 300
    assert gaps[0].actual_delta_seconds == 420  # 00:05 -> 00:12
    assert gaps[0].missing_bars == 0  # 420 // 300 - 1 = 0 (konservativ)


# 13: leere CSV liefert [] und keine Gaps (auch mit gesetztem Timeframe).
def test_csv_empty_with_timeframe_no_gaps():
    src = HistoricalFileSource(_fixture("ohlcv_empty.csv"), timeframe="5m")
    bars = src.market_data()
    assert bars == []
    assert src.gap_report() == ()


# --------------------------------------------------------------------------- #
# LQ-003 Phase 3: Daten-Metadaten (Instrument/Quelle/Timeframe)
# --------------------------------------------------------------------------- #
# 1–3: Default-Metadaten werden erzeugt.
def test_source_creates_default_metadata():
    src = HistoricalFileSource(_fixture("ohlcv_valid.csv"))
    assert isinstance(src.metadata, DataSourceMetadata)
    assert src.metadata.source_type == "local_csv"
    assert src.metadata.source_path == _fixture("ohlcv_valid.csv")
    # nicht gesetzte Felder bleiben defensiv "unknown".
    assert src.metadata.asset_class == "unknown"


# 4: Default-Metadaten übernehmen den Timeframe.
def test_default_metadata_takes_timeframe():
    src = HistoricalFileSource(_fixture("ohlcv_no_gap_5m.csv"), timeframe="5m")
    assert src.metadata.timeframe == "5m"


# 5: Custom-Metadaten werden akzeptiert.
def test_custom_metadata_accepted():
    meta = DataSourceMetadata(asset_class="crypto", exchange="binance", symbol="ETHUSDT")
    src = HistoricalFileSource(_fixture("ohlcv_valid.csv"), metadata=meta)
    assert src.metadata.symbol == "ETHUSDT"
    assert src.metadata.exchange == "binance"
    assert src.metadata.asset_class == "crypto"


# 6: Custom-Metadaten mit leerem source_path werden um den Pfad ergänzt.
def test_custom_metadata_empty_path_filled():
    meta = DataSourceMetadata(symbol="BTCUSDT", source_path="")
    src = HistoricalFileSource(_fixture("ohlcv_valid.csv"), metadata=meta)
    assert src.metadata.source_path == _fixture("ohlcv_valid.csv")
    assert src.metadata.symbol == "BTCUSDT"


# 7: Custom-Metadaten mit timeframe=None werden um den Source-Timeframe ergänzt.
def test_custom_metadata_timeframe_filled_from_source():
    meta = DataSourceMetadata(symbol="BTCUSDT")  # timeframe=None
    src = HistoricalFileSource(_fixture("ohlcv_no_gap_1h.csv"), timeframe="1h", metadata=meta)
    assert src.metadata.timeframe == "1h"


# 8: Metadata ist immutable.
def test_metadata_is_immutable():
    src = HistoricalFileSource(_fixture("ohlcv_valid.csv"))
    raised = False
    try:
        src.metadata.symbol = "X"  # type: ignore[misc]
    except Exception:
        raised = True
    assert raised, "DataSourceMetadata muss frozen/immutable sein"


# 9: Bestehende Aufrufe ohne Metadata-Argument bleiben kompatibel.
def test_existing_source_calls_still_compatible():
    src = HistoricalFileSource(_fixture("ohlcv_valid.csv"))
    bars = src.market_data()
    assert len(bars) == 3


# 10: BacktestResult.parameters enthält die Daten-Metadaten (Quelle trägt sie).
def test_runner_parameters_include_data_metadata():
    source = HistoricalFileSource(
        _fixture("ohlcv_valid.csv"),
        timeframe="1m",
        metadata=DataSourceMetadata(asset_class="crypto", exchange="binance", symbol="BTCUSDT"),
    )
    res = BacktestRunner(source, RiskEngine(_valid_limits()), CostModel()).run()
    assert res.parameters["data_asset_class"] == "crypto"
    assert res.parameters["data_exchange"] == "binance"
    assert res.parameters["data_symbol"] == "BTCUSDT"
    assert res.parameters["data_timeframe"] == "1m"  # aus Source-Timeframe ergänzt
    assert res.parameters["data_source_type"] == "local_csv"
    # weiterhin ausschließlich skalare Parameter.
    for value in res.parameters.values():
        assert isinstance(value, (str, int, float, bool))


# Zusatz: Quelle ohne Metadata (FakeSource) fügt KEINE data_*-Parameter hinzu.
def test_runner_without_metadata_source_has_no_data_params():
    res = BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0]), RiskEngine(_valid_limits()), CostModel()
    ).run()
    assert "data_symbol" not in res.parameters
    assert "data_source_type" not in res.parameters
