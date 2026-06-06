"""Reine Signal-Tests für MidBreakoutStrategy (LQ-006 Phase 1).

Spec: Strategie-v0-Spezifikation (Mid-Breakout, OHLCV-Proxy).

Bewusst NUR Strategie-Ebene (keine Runner-/RiskEngine-Integration — die folgt
in Phase 2). Nutzt ausschließlich Standardbibliothek + bestehende
Projektklassen. Keine echte Handelslogik, keine Bewertung, keine Optimierung.
"""

import math
from datetime import datetime, timezone

from liquent.backtesting.reporting import (
    summarize_backtest_result,
    summary_to_dict,
    summary_to_markdown,
)
from liquent.backtesting.runner import BacktestRunner, CostModel
from liquent.domain.models import Direction, MarketData, Signal
from liquent.risk.engine import RiskEngine, RiskLimits
from liquent.strategy import MidBreakoutStrategy


def _bars(mids: list[float]) -> list[MarketData]:
    """Baut Bars aus einer Mid-Liste (bid/ask symmetrisch -> _mid == m)."""
    return [
        MarketData(
            timestamp=datetime(2026, 6, 2, 0, i, tzinfo=timezone.utc),
            bid=m - 0.5,
            ask=m + 0.5,
            volume=1.0,
        )
        for i, m in enumerate(mids)
    ]


def _ts(i: int) -> datetime:
    return datetime(2026, 6, 2, 0, i, tzinfo=timezone.utc)


def _expect_value_error(fn) -> None:
    raised = False
    try:
        fn()
    except ValueError:
        raised = True
    assert raised, "erwartete ValueError wurde nicht ausgelöst"


# 1: Zu wenig Daten -> leeres Tuple.
def test_too_little_data_returns_empty():
    strat = MidBreakoutStrategy(lookback_bars=2, stop_distance_pct=0.1)
    # n=2 -> last_entry=0 < lookback 2 -> keine Signale.
    result = strat.generate_signals(_bars([100.0, 101.0]))
    assert result == ()
    assert isinstance(result, tuple)
    # Auch komplett leere Eingabe ist stabil.
    assert strat.generate_signals([]) == ()


# 2: Long-Breakout erzeugt genau ein LONG-Signal am erwarteten Timestamp.
def test_long_breakout_single_signal_at_expected_timestamp():
    strat = MidBreakoutStrategy(lookback_bars=2, stop_distance_pct=0.1)
    # i=2: window [10,10], cur 11 > 10 -> LONG. i=3: window [10,11], cur 10 -> nichts.
    signals = strat.generate_signals(_bars([10.0, 10.0, 11.0, 10.0, 10.0]))
    assert len(signals) == 1
    assert signals[0].direction == Direction.LONG
    assert signals[0].timestamp == _ts(2)
    assert signals[0].strength == 1.0


# 3: Short-Breakout erzeugt genau ein SHORT-Signal bei allow_short=True.
def test_short_breakout_single_signal_when_allowed():
    strat = MidBreakoutStrategy(lookback_bars=2, stop_distance_pct=0.1, allow_short=True)
    # i=2: window [10,10], cur 9 < 10 -> SHORT. i=3: window [10,9], cur 10 -> nichts.
    signals = strat.generate_signals(_bars([10.0, 10.0, 9.0, 10.0, 10.0]))
    assert len(signals) == 1
    assert signals[0].direction == Direction.SHORT
    assert signals[0].timestamp == _ts(2)


# 4: Short-Breakout erzeugt kein Signal bei allow_short=False.
def test_short_breakout_suppressed_when_disallowed():
    strat = MidBreakoutStrategy(lookback_bars=2, stop_distance_pct=0.1, allow_short=False)
    signals = strat.generate_signals(_bars([10.0, 10.0, 9.0, 10.0, 10.0]))
    assert signals == ()


# 5: LONG stop_price liegt unter Entry-Mid und ist > 0.
def test_long_stop_below_entry_and_positive():
    strat = MidBreakoutStrategy(lookback_bars=2, stop_distance_pct=0.1)
    signals = strat.generate_signals(_bars([10.0, 10.0, 11.0, 10.0, 10.0]))
    sig = signals[0]
    assert sig.stop_price is not None
    assert sig.stop_price < 11.0
    assert sig.stop_price > 0.0
    assert math.isclose(sig.stop_price, 11.0 * (1 - 0.1), rel_tol=1e-9)


# 6: SHORT stop_price liegt über Entry-Mid.
def test_short_stop_above_entry():
    strat = MidBreakoutStrategy(lookback_bars=2, stop_distance_pct=0.1)
    signals = strat.generate_signals(_bars([10.0, 10.0, 9.0, 10.0, 10.0]))
    sig = signals[0]
    assert sig.stop_price is not None
    assert sig.stop_price > 9.0
    assert math.isclose(sig.stop_price, 9.0 * (1 + 0.1), rel_tol=1e-9)


# 7: lookback_bars <= 0 -> ValueError.
def test_invalid_lookback_raises():
    _expect_value_error(lambda: MidBreakoutStrategy(lookback_bars=0, stop_distance_pct=0.1))
    _expect_value_error(lambda: MidBreakoutStrategy(lookback_bars=-1, stop_distance_pct=0.1))


# 8: stop_distance_pct <= 0 -> ValueError.
def test_invalid_stop_distance_low_raises():
    _expect_value_error(lambda: MidBreakoutStrategy(lookback_bars=2, stop_distance_pct=0.0))
    _expect_value_error(lambda: MidBreakoutStrategy(lookback_bars=2, stop_distance_pct=-0.1))


# 9: stop_distance_pct >= 1.0 -> ValueError.
def test_invalid_stop_distance_high_raises():
    _expect_value_error(lambda: MidBreakoutStrategy(lookback_bars=2, stop_distance_pct=1.0))
    _expect_value_error(lambda: MidBreakoutStrategy(lookback_bars=2, stop_distance_pct=1.5))


# 10: min_strength außerhalb [0, 1] -> ValueError.
def test_invalid_min_strength_raises():
    _expect_value_error(
        lambda: MidBreakoutStrategy(lookback_bars=2, stop_distance_pct=0.1, min_strength=-0.1)
    )
    _expect_value_error(
        lambda: MidBreakoutStrategy(lookback_bars=2, stop_distance_pct=0.1, min_strength=1.1)
    )


# 11: Determinismus -> gleicher Input liefert identische Signale.
def test_deterministic_same_input_same_signals():
    mids = [10.0, 10.0, 11.0, 9.0, 12.0, 8.0]
    strat = MidBreakoutStrategy(lookback_bars=2, stop_distance_pct=0.1)
    res_a = strat.generate_signals(_bars(mids))
    res_b = strat.generate_signals(_bars(mids))
    assert res_a == res_b
    # Auch eine frische Instanz mit gleicher Konfiguration ist deckungsgleich.
    res_c = MidBreakoutStrategy(lookback_bars=2, stop_distance_pct=0.1).generate_signals(
        _bars(mids)
    )
    assert res_a == res_c


# 12: Kein Signal bei Gleichstand mid[i] == prev_high (strikter Vergleich).
def test_no_signal_on_tie():
    strat = MidBreakoutStrategy(lookback_bars=2, stop_distance_pct=0.1)
    # Konstante Mids: cur ist nie strikt > prev_high oder < prev_low.
    assert strat.generate_signals(_bars([10.0, 10.0, 10.0, 10.0])) == ()


# 13: Höchstens ein Signal pro Timestamp (keine Duplikate).
def test_at_most_one_signal_per_timestamp():
    mids = [10.0, 10.0, 11.0, 9.0, 12.0, 8.0, 13.0]
    signals = MidBreakoutStrategy(lookback_bars=2, stop_distance_pct=0.1).generate_signals(
        _bars(mids)
    )
    timestamps = [s.timestamp for s in signals]
    assert len(timestamps) == len(set(timestamps))
    # Jedes Element ist ein echtes Signal mit gesetztem Stop.
    for s in signals:
        assert isinstance(s, Signal)
        assert s.stop_price is not None


# 14: Kein Signal auf dem letzten Bar (kein Folge-Bar).
def test_no_signal_on_last_bar():
    strat = MidBreakoutStrategy(lookback_bars=2, stop_distance_pct=0.1)
    # Einziger potenzieller Breakout läge auf dem letzten Bar (i=3) -> verworfen.
    assert strat.generate_signals(_bars([10.0, 10.0, 10.0, 15.0])) == ()


# Optional: keine FLAT-Signale.
def test_never_emits_flat():
    mids = [10.0, 10.0, 11.0, 9.0, 12.0]
    signals = MidBreakoutStrategy(lookback_bars=2, stop_distance_pct=0.1).generate_signals(
        _bars(mids)
    )
    assert all(s.direction in (Direction.LONG, Direction.SHORT) for s in signals)


# Optional: das neue Modul referenziert keine Netzwerk-/Exchange-/Live-/Paper-Pfade.
def test_module_has_no_network_live_or_paper_paths():
    import inspect

    from liquent.strategy import mid_breakout as module

    source_code = inspect.getsource(module)
    forbidden = (
        "socket", "urllib", "requests", "http://", "https://",
        "websocket", "ccxt", "live_order", "place_order",
        "paper_trading", "api_key", "secret",
    )
    for token in forbidden:
        assert token not in source_code, f"Modul darf {token!r} nicht referenzieren"


# --------------------------------------------------------------------------- #
# LQ-006 Phase 2: Runner-Integration mit percent_risk (Risk-First End-to-End)
# --------------------------------------------------------------------------- #
# Reine In-Memory-Integration — KEINE CSV-Daten, kein Netzwerk, keine Exchange.


class _MidSource:
    """In-Memory-DataSource aus einer Mid-Liste (bid/ask symmetrisch).

    Erfüllt die ``DataSource``-Schnittstelle strukturell. Keine Datei, kein
    Netzwerk, keine Metadaten/History (Runner liest beides defensiv optional).
    """

    def __init__(self, mids: list[float]) -> None:
        self._bars = _bars(mids)

    def market_data(self):
        return list(self._bars)

    def order_book_snapshots(self):
        return []


def _pct_risk_limits(**overrides) -> RiskLimits:
    """percent_risk-Limits gemäß LQ-006-Phase-2-Vorgabe (großzügige Caps)."""
    base = dict(
        max_position_size=100.0,
        max_total_exposure=100_000.0,
        risk_per_trade=1.0,
        max_daily_drawdown=10_000.0,
        sizing_mode="percent_risk",
        risk_per_trade_pct=0.01,
        max_position_notional=100_000.0,
        max_daily_loss=0.0,
        max_losing_streak=0,
    )
    base.update(overrides)
    return RiskLimits(**base)


# Long-Szenario aus der Spezifikation: Entry bei i=3 (106 > max(100,101,102)),
# Exit am Folgebar (108). stop_distance_pct=0.05.
_LONG_MIDS = [100.0, 101.0, 102.0, 106.0, 108.0]
# Short-Szenario: Entry bei i=3 (94 < min(100,99,98)), Exit am Folgebar (92).
_SHORT_MIDS = [100.0, 99.0, 98.0, 94.0, 92.0]
_STARTING_EQUITY = 10_000.0
_STOP_PCT = 0.05


def _long_runner(**risk_overrides) -> BacktestRunner:
    return BacktestRunner(
        _MidSource(_LONG_MIDS),
        RiskEngine(_pct_risk_limits(**risk_overrides)),
        CostModel(fee_rate=0.0, spread=0.0, slippage=0.0),
        strategy=MidBreakoutStrategy(lookback_bars=3, stop_distance_pct=_STOP_PCT),
        initial_equity=_STARTING_EQUITY,
    )


def _expected_size(entry: float, stop: float) -> float:
    """Repliziert die percent_risk-Sizing-Formel der Engine (ohne Caps)."""
    stop_distance = abs(entry - stop)
    risk_amount = _STARTING_EQUITY * 0.01
    return risk_amount / stop_distance


# 1: MidBreakoutStrategy + Runner + percent_risk erzeugt einen Long-Trade.
def test_integration_long_produces_trade():
    res = _long_runner().run()
    assert res.number_of_trades == 1
    assert res.trades[0].side == "long"


# 2: Long-Trade nutzt die erwartete percent_risk-Size.
def test_integration_long_expected_size():
    res = _long_runner().run()
    entry = 106.0
    stop = entry * (1 - _STOP_PCT)  # 100.7
    expected = _expected_size(entry, stop)  # 100 / 5.3
    assert math.isclose(res.trades[0].quantity, expected, rel_tol=1e-9)


# 3: Long-Trade PnL nutzt die erwartete Size (kostenfrei).
def test_integration_long_expected_pnl():
    res = _long_runner().run()
    entry, exit_ = 106.0, 108.0
    stop = entry * (1 - _STOP_PCT)
    expected_size = _expected_size(entry, stop)
    expected_gross = (exit_ - entry) * expected_size
    assert math.isclose(res.trades[0].gross_pnl, expected_gross, rel_tol=1e-9)
    # Kostenfrei -> net == gross; Equity steigt um den PnL.
    assert math.isclose(res.trades[0].net_pnl, expected_gross, rel_tol=1e-9)
    assert math.isclose(
        res.ending_equity, _STARTING_EQUITY + expected_gross, rel_tol=1e-9
    )


# 4: Long-Trade-Signal trägt einen stop_price (percent_risk-Voraussetzung).
def test_integration_long_signal_has_stop_price():
    signals = MidBreakoutStrategy(
        lookback_bars=3, stop_distance_pct=_STOP_PCT
    ).generate_signals(_bars(_LONG_MIDS))
    assert len(signals) == 1
    assert signals[0].stop_price is not None
    assert signals[0].stop_price < 106.0  # Long-Stop unter Entry
    # Und der Trade entsteht tatsächlich (Stop wird vom Gate akzeptiert).
    assert _long_runner().run().number_of_trades == 1


# 5: approved_signals == number_of_trades (kein Bypass, keine Doppelung).
def test_integration_approved_equals_trades():
    res = _long_runner().run()
    assert res.approved_signals == res.number_of_trades == 1


# 6: rejected_signals == 0 im sauberen Long-Szenario.
def test_integration_long_no_rejections():
    res = _long_runner().run()
    assert res.rejected_signals == 0
    assert res.parameters["signals_total"] == 1


# 7: Short-Trade funktioniert mit allow_short=True.
def test_integration_short_produces_trade():
    res = BacktestRunner(
        _MidSource(_SHORT_MIDS),
        RiskEngine(_pct_risk_limits()),
        CostModel(),
        strategy=MidBreakoutStrategy(
            lookback_bars=3, stop_distance_pct=_STOP_PCT, allow_short=True
        ),
        initial_equity=_STARTING_EQUITY,
    ).run()
    assert res.number_of_trades == 1
    assert res.trades[0].side == "short"
    assert res.approved_signals == 1
    assert res.rejected_signals == 0


# 8: Short-Trade nutzt die erwartete percent_risk-Size.
def test_integration_short_expected_size():
    res = BacktestRunner(
        _MidSource(_SHORT_MIDS),
        RiskEngine(_pct_risk_limits()),
        CostModel(),
        strategy=MidBreakoutStrategy(
            lookback_bars=3, stop_distance_pct=_STOP_PCT, allow_short=True
        ),
        initial_equity=_STARTING_EQUITY,
    ).run()
    entry = 94.0
    stop = entry * (1 + _STOP_PCT)  # 98.7
    expected = _expected_size(entry, stop)  # 100 / 4.7
    assert math.isclose(res.trades[0].quantity, expected, rel_tol=1e-9)


# 9: Short-Trade PnL nutzt die erwartete Size (kostenfrei).
def test_integration_short_expected_pnl():
    res = BacktestRunner(
        _MidSource(_SHORT_MIDS),
        RiskEngine(_pct_risk_limits()),
        CostModel(),
        strategy=MidBreakoutStrategy(
            lookback_bars=3, stop_distance_pct=_STOP_PCT, allow_short=True
        ),
        initial_equity=_STARTING_EQUITY,
    ).run()
    entry, exit_ = 94.0, 92.0
    stop = entry * (1 + _STOP_PCT)
    expected_size = _expected_size(entry, stop)
    # Short: gross = (entry - exit) * size.
    expected_gross = (entry - exit_) * expected_size
    assert math.isclose(res.trades[0].gross_pnl, expected_gross, rel_tol=1e-9)
    assert math.isclose(res.trades[0].net_pnl, expected_gross, rel_tol=1e-9)


# 10: allow_short=False erzeugt im Short-Breakout-Szenario keinen Trade.
def test_integration_short_disallowed_no_trade():
    res = BacktestRunner(
        _MidSource(_SHORT_MIDS),
        RiskEngine(_pct_risk_limits()),
        CostModel(),
        strategy=MidBreakoutStrategy(
            lookback_bars=3, stop_distance_pct=_STOP_PCT, allow_short=False
        ),
        initial_equity=_STARTING_EQUITY,
    ).run()
    assert res.parameters["signals_total"] == 0
    assert res.number_of_trades == 0
    assert res.trades == ()


# 11: Zu wenig Daten -> keine Signale, keine Trades, stabiles Ergebnis.
def test_integration_too_little_data_no_trades():
    res = BacktestRunner(
        _MidSource([100.0, 101.0]),  # n=2 < lookback 3
        RiskEngine(_pct_risk_limits()),
        CostModel(),
        strategy=MidBreakoutStrategy(lookback_bars=3, stop_distance_pct=_STOP_PCT),
        initial_equity=_STARTING_EQUITY,
    ).run()
    assert res.parameters["signals_total"] == 0
    assert res.number_of_trades == 0
    assert res.ending_equity == res.starting_equity


# 12: BacktestResult.parameters trägt den Strategie-Namen + percent_risk-Felder.
def test_integration_parameters_expose_strategy_and_sizing():
    res = _long_runner().run()
    assert res.parameters["strategy"] == "MidBreakoutStrategy"
    assert res.parameters["sizing_mode"] == "percent_risk"
    assert res.parameters["risk_per_trade_pct"] == 0.01
    # weiterhin ausschließlich skalare Parameter.
    for value in res.parameters.values():
        assert isinstance(value, (str, int, float, bool))


# 13: Reporting kann das Result fehlerfrei zusammenfassen (Markdown + Dict).
def test_integration_reporting_summarizes_result():
    res = _long_runner().run()
    summary = summarize_backtest_result(res, title="LQ-006 MidBreakout")
    assert summary.strategy_name == "MidBreakoutStrategy"

    markdown = summary_to_markdown(summary)
    assert isinstance(markdown, str)
    assert "MidBreakoutStrategy" in markdown
    # percent_risk-spezifische Risk Notes erscheinen (deskriptiv, keine Empfehlung).
    assert "Percentage risk sizing was used." in markdown
    assert "A stop_price is required for percent_risk sizing." in markdown

    as_dict = summary_to_dict(summary)
    assert as_dict["strategy_name"] == "MidBreakoutStrategy"
    assert as_dict["safety_flags"] == {
        "live_execution": False,
        "network_calls": False,
        "paper_trading": False,
    }


# 14: Integrationspfad bleibt frei von Live-/Netzwerk-/Paper-Trading.
def test_integration_no_live_network_or_paper_paths():
    # Sicherheits-Invarianten direkt aus dem realen Lauf.
    res = _long_runner().run()
    assert res.parameters["mode"] == "analysis"
    assert res.parameters["live_execution"] is False
    assert res.parameters["network_calls"] is False
    assert res.parameters["paper_trading"] is False

    # Zusätzlich: das Produktiv-Strategiemodul referenziert keine solchen Pfade.
    import inspect

    from liquent.strategy import mid_breakout as module

    source_code = inspect.getsource(module)
    forbidden = (
        "socket", "urllib", "requests", "http://", "https://",
        "websocket", "ccxt", "live_order", "place_order",
        "paper_trading", "api_key", "secret",
    )
    for token in forbidden:
        assert token not in source_code, f"Modul darf {token!r} nicht referenzieren"
