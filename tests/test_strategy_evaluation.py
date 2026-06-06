"""End-to-End-Auswertung MidBreakoutStrategy v0 über CSV-Fixtures (LQ-007 Phase 1).

Pipeline (rein lokal, deterministisch):
    tests/fixtures/*.csv
    -> HistoricalFileSource (timeframe="5m", history_policy="flag", metadata)
    -> MidBreakoutStrategy
    -> RiskEngine (sizing_mode="percent_risk")
    -> BacktestRunner
    -> BacktestResult
    -> Reporting (Summary / Markdown / Dict)

Ziel ist die Verifikation von Mechanik und Korrektheit der Pipeline an einer
echten CSV-Quelle — KEINE Performance- oder Profitabilitätsbewertung, keine
Handelsempfehlung. Es werden ausschließlich synthetische Fixtures genutzt; keine
echten Marktdaten, kein Netzwerk, keine Exchange, keine Zugangsdaten.
"""

import math
from pathlib import Path

from liquent.backtesting.reporting import (
    summarize_backtest_result,
    summary_to_dict,
    summary_to_markdown,
)
from liquent.backtesting.runner import BacktestRunner, CostModel
from liquent.data.sources import DataSourceMetadata, HistoricalFileSource
from liquent.risk.engine import RiskEngine, RiskLimits
from liquent.strategy import MidBreakoutStrategy

_FIXTURES = Path(__file__).parent / "fixtures"
_STARTING_EQUITY = 10_000.0
_STOP_PCT = 0.05


def _fixture(name: str) -> str:
    return str(_FIXTURES / name)


def _source(name: str) -> HistoricalFileSource:
    """CSV-Quelle mit Timeframe + Metadaten (für data_* / data_history_*)."""
    return HistoricalFileSource(
        _fixture(name),
        timeframe="5m",
        history_policy="flag",
        metadata=DataSourceMetadata(
            asset_class="crypto", exchange="synthetic", symbol="TESTUSDT"
        ),
    )


def _limits() -> RiskLimits:
    """percent_risk-Limits gemäß LQ-007-Vorgabe (großzügige Caps)."""
    return RiskLimits(
        max_position_size=100.0,
        max_total_exposure=100_000.0,
        risk_per_trade=0.0,  # in percent_risk irrelevant
        max_daily_drawdown=10_000.0,
        sizing_mode="percent_risk",
        risk_per_trade_pct=0.01,
        max_position_notional=100_000.0,
        max_daily_loss=0.0,
        max_losing_streak=0,
    )


def _run(name: str, *, allow_short: bool = True):
    return BacktestRunner(
        _source(name),
        RiskEngine(_limits()),
        CostModel(fee_rate=0.0, spread=0.0, slippage=0.0),
        strategy=MidBreakoutStrategy(
            lookback_bars=3,
            stop_distance_pct=_STOP_PCT,
            min_strength=0.0,
            allow_short=allow_short,
        ),
        initial_equity=_STARTING_EQUITY,
    ).run()


def _expected_size(entry: float, stop: float) -> float:
    """Repliziert die percent_risk-Sizing-Formel der Engine (ohne Caps)."""
    stop_distance = abs(entry - stop)
    risk_amount = _STARTING_EQUITY * 0.01
    return risk_amount / stop_distance


# --------------------------------------------------------------------------- #
# Long-Szenario
# --------------------------------------------------------------------------- #
# 1: Long-Fixture wird über HistoricalFileSource geladen.
def test_long_fixture_loads():
    bars = _source("strategy_mid_breakout_long.csv").market_data()
    assert len(bars) == 5
    # mid == close (bid = ask = close).
    assert [(b.bid + b.ask) / 2 for b in bars] == [100.0, 100.0, 100.0, 106.0, 108.0]


# 2 + 3: Backtest erzeugt genau einen Long-Trade.
def test_long_single_long_trade():
    res = _run("strategy_mid_breakout_long.csv")
    assert res.number_of_trades == 1
    assert res.trades[0].side == "long"


# 4 + 5: Gate-Counts im sauberen Long-Szenario.
def test_long_gate_counts():
    res = _run("strategy_mid_breakout_long.csv")
    assert res.approved_signals == res.number_of_trades == 1
    assert res.rejected_signals == 0
    assert res.parameters["signals_total"] == 1


# 6: Erwartete percent_risk-Size.
def test_long_expected_size():
    res = _run("strategy_mid_breakout_long.csv")
    entry = 106.0
    stop = entry * (1 - _STOP_PCT)  # 100.7
    assert math.isclose(res.trades[0].quantity, _expected_size(entry, stop), rel_tol=1e-9)


# 7: Erwarteter PnL und ending_equity (frictionless -> net == gross).
def test_long_expected_pnl():
    res = _run("strategy_mid_breakout_long.csv")
    entry, exit_ = 106.0, 108.0
    size = _expected_size(entry, entry * (1 - _STOP_PCT))
    gross = (exit_ - entry) * size
    assert math.isclose(res.trades[0].gross_pnl, gross, rel_tol=1e-9)
    assert math.isclose(res.trades[0].net_pnl, gross, rel_tol=1e-9)
    assert math.isclose(res.ending_equity, _STARTING_EQUITY + gross, rel_tol=1e-9)


# --------------------------------------------------------------------------- #
# Short-Szenario
# --------------------------------------------------------------------------- #
# 8 + 9: Short-Fixture erzeugt genau einen Short-Trade (allow_short=True).
def test_short_single_short_trade():
    res = _run("strategy_mid_breakout_short.csv", allow_short=True)
    assert res.number_of_trades == 1
    assert res.trades[0].side == "short"
    assert res.approved_signals == 1
    assert res.rejected_signals == 0


# 10: Erwartete percent_risk-Size (Short).
def test_short_expected_size():
    res = _run("strategy_mid_breakout_short.csv", allow_short=True)
    entry = 94.0
    stop = entry * (1 + _STOP_PCT)  # 98.7
    assert math.isclose(res.trades[0].quantity, _expected_size(entry, stop), rel_tol=1e-9)


# 11: Erwarteter PnL und ending_equity (Short).
def test_short_expected_pnl():
    res = _run("strategy_mid_breakout_short.csv", allow_short=True)
    entry, exit_ = 94.0, 92.0
    size = _expected_size(entry, entry * (1 + _STOP_PCT))
    gross = (entry - exit_) * size  # Short
    assert math.isclose(res.trades[0].gross_pnl, gross, rel_tol=1e-9)
    assert math.isclose(res.trades[0].net_pnl, gross, rel_tol=1e-9)
    assert math.isclose(res.ending_equity, _STARTING_EQUITY + gross, rel_tol=1e-9)


# --------------------------------------------------------------------------- #
# allow_short=False
# --------------------------------------------------------------------------- #
# 12: Short-Fixture mit allow_short=False -> kein Signal, kein Trade.
def test_short_disallowed_no_trade():
    res = _run("strategy_mid_breakout_short.csv", allow_short=False)
    assert res.parameters["signals_total"] == 0
    assert res.number_of_trades == 0
    assert res.ending_equity == _STARTING_EQUITY


# --------------------------------------------------------------------------- #
# No-Signal-Szenario
# --------------------------------------------------------------------------- #
# 13: No-Signal-Fixture -> 0 Signale, 0 Trades, keine Gate-Durchläufe.
def test_no_signal_fixture_no_trade():
    res = _run("strategy_mid_breakout_no_signal.csv")
    assert res.parameters["signals_total"] == 0
    assert res.number_of_trades == 0
    assert res.approved_signals == 0
    assert res.rejected_signals == 0
    assert res.ending_equity == _STARTING_EQUITY


# --------------------------------------------------------------------------- #
# Metadata und HistoryReport in BacktestResult.parameters
# --------------------------------------------------------------------------- #
# 14: Daten-Herkunfts-Metadaten erscheinen in parameters.
def test_parameters_include_metadata():
    res = _run("strategy_mid_breakout_long.csv")
    assert res.parameters["data_asset_class"] == "crypto"
    assert res.parameters["data_exchange"] == "synthetic"
    assert res.parameters["data_symbol"] == "TESTUSDT"
    assert res.parameters["data_timeframe"] == "5m"
    assert res.parameters["data_source_type"] == "local_csv"
    assert res.parameters["data_source_path"].endswith(
        "strategy_mid_breakout_long.csv"
    )
    # weiterhin ausschließlich skalare Parameter.
    for value in res.parameters.values():
        assert isinstance(value, (str, int, float, bool))


# 15: HistoryReport-Parameter erscheinen (Mindesthistorie unterschritten).
def test_parameters_include_history_report():
    res = _run("strategy_mid_breakout_long.csv")
    assert res.parameters["data_history_timeframe"] == "5m"
    assert res.parameters["data_history_required_bars"] == 8640
    assert res.parameters["data_history_required_days"] == 30
    assert res.parameters["data_history_meets_minimum"] is False
    assert res.parameters["data_history_policy"] == "flag"


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
# 16 + 17: Summary + Markdown enthalten die erwarteten Felder/Risk-Notes.
def test_reporting_markdown_contains_expected_fields():
    res = _run("strategy_mid_breakout_long.csv")
    summary = summarize_backtest_result(res, title="LQ-007 MidBreakout Auswertung")
    assert summary.strategy_name == "MidBreakoutStrategy"

    markdown = summary_to_markdown(summary)
    assert isinstance(markdown, str)
    for token in (
        "sizing_mode",
        "percent_risk",
        "data_symbol",
        "TESTUSDT",
        "data_history_meets_minimum",
        "Percentage risk sizing was used.",
        "A stop_price is required for percent_risk sizing.",
    ):
        assert token in markdown, f"Markdown muss {token!r} enthalten"


# 18: summary_to_dict läuft fehlerfrei und enthält Parameter.
def test_reporting_dict_contains_parameters():
    res = _run("strategy_mid_breakout_long.csv")
    summary = summarize_backtest_result(res)
    as_dict = summary_to_dict(summary)
    assert as_dict["strategy_name"] == "MidBreakoutStrategy"
    assert as_dict["parameters"]["sizing_mode"] == "percent_risk"
    assert as_dict["parameters"]["data_symbol"] == "TESTUSDT"


# --------------------------------------------------------------------------- #
# Safety
# --------------------------------------------------------------------------- #
# 19: Sicherheits-Invarianten direkt aus dem Lauf.
def test_safety_flags_invariants():
    res = _run("strategy_mid_breakout_long.csv")
    assert res.parameters["mode"] == "analysis"
    assert res.parameters["live_execution"] is False
    assert res.parameters["network_calls"] is False
    assert res.parameters["paper_trading"] is False


# 20: Statische Prüfung dieses Testmoduls — keine Netzwerk-/Exchange-/Credential-
#     /Marketing-Pfade. Hinweis: die Safety-Flag-Feldnamen (live_execution etc.)
#     werden bewusst NICHT geprüft — sie sind legitime Datenreferenzen (Test 19),
#     kein Verstoß. Die Verbotsbegriffe sind aus Fragmenten zusammengesetzt,
#     damit die Liste sich nicht selbst trifft.
def test_module_has_no_forbidden_paths_or_terms():
    import inspect

    import tests.test_strategy_evaluation as module

    source_code = inspect.getsource(module).lower()
    forbidden = [
        "soc" + "ket",
        "url" + "lib",
        "req" + "uests",
        "ht" + "tp://",
        "ht" + "tps://",
        "web" + "soc" + "ket",
        "cc" + "xt",
        "live_" + "order",
        "place_" + "order",
        "api_" + "key",
        "sec" + "ret",
        "pass" + "word",
        "profit" + "abel",
        "garan" + "tiert",
        "live-" + "ready",
        "sicherer " + "gewinn",
        "empfehlung " + "kaufen",
        "profit" + "able",
        "guaran" + "teed",
    ]
    for token in forbidden:
        assert token not in source_code, f"Testmodul darf {token!r} nicht enthalten"
