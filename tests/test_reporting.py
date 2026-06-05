"""Reporting-/Experiment-Export-Tests (LQ-005 Phase 5).

Spec: liquent/06_Backtesting/Backtesting_Framework_Spec.md

Deckt die interne Serialisierungsbasis ab: Überführung eines BacktestResult in
eine immutable BacktestExperimentSummary, deterministischer Markdown-Export und
die defensive Behandlung der Sicherheits-Flags. KEIN Obsidian-/Datei-Schreiben.
"""

import inspect
import json
from datetime import datetime, timezone

from liquent.backtesting.reporting import (
    BacktestExperimentSummary,
    summarize_backtest_result,
    summary_to_dict,
    summary_to_markdown,
)
from liquent.backtesting.runner import BacktestResult, BacktestRunner, CostModel
from liquent.domain.models import MarketData
from liquent.risk.engine import RiskEngine, RiskLimits


class _FakeSource:
    """Deterministische In-Memory-Quelle aus Mid-Preisen (kein I/O)."""

    def __init__(self, mids):
        self._mids = mids

    def market_data(self):
        return [
            MarketData(
                timestamp=datetime(2026, 6, 2, 0, i, tzinfo=timezone.utc),
                bid=m - 0.5,
                ask=m + 0.5,
                volume=1.0,
            )
            for i, m in enumerate(self._mids)
        ]

    def order_book_snapshots(self):
        return []


def _valid_limits() -> RiskLimits:
    return RiskLimits(
        max_position_size=10.0,
        max_total_exposure=100.0,
        risk_per_trade=5.0,
        max_daily_drawdown=1000.0,
    )


def _sample_result() -> BacktestResult:
    return BacktestRunner(
        _FakeSource([100.0, 102.0, 105.0]),
        RiskEngine(_valid_limits()),
        CostModel(fee_rate=0.001, spread=0.05, slippage=0.0005),
        seed=7,
        initial_equity=1000.0,
    ).run()


# 1: experiment_id wird übernommen.
def test_summary_takes_over_experiment_id():
    res = _sample_result()
    summary = summarize_backtest_result(res)
    assert isinstance(summary, BacktestExperimentSummary)
    assert summary.experiment_id == res.experiment_id


# 2: Summary enthält strategy_name.
def test_summary_contains_strategy_name():
    summary = summarize_backtest_result(_sample_result())
    assert summary.strategy_name == "MomentumStubStrategy"


# 3: Summary enthält Metriken.
def test_summary_contains_metrics():
    res = _sample_result()
    summary = summarize_backtest_result(res)
    assert summary.metrics == res.metrics
    for key in ("win_rate", "profit_factor", "max_drawdown", "number_of_trades"):
        assert key in summary.metrics


# 4: Summary enthält Parameter.
def test_summary_contains_parameters():
    res = _sample_result()
    summary = summarize_backtest_result(res)
    assert summary.parameters == res.parameters
    assert summary.parameters["seed"] == 7


# 5: Safety Flags sind False.
def test_safety_flags_are_false():
    summary = summarize_backtest_result(_sample_result())
    assert summary.safety_flags["live_execution"] is False
    assert summary.safety_flags["network_calls"] is False
    assert summary.safety_flags["paper_trading"] is False


# 6: Fehlende Safety Flags werden defensiv gesetzt + dokumentiert.
def test_missing_safety_flags_defaulted():
    bare = BacktestResult(
        experiment_id="lq005-test",
        number_of_trades=0,
        approved_signals=0,
        rejected_signals=0,
        starting_equity=0.0,
        ending_equity=0.0,
        equity_curve=(0.0,),
        metrics={"number_of_trades": 0},
        trades=(),
        parameters={"strategy": "MomentumStubStrategy"},  # bewusst ohne Flags
    )
    summary = summarize_backtest_result(bare)
    assert summary.safety_flags["live_execution"] is False
    assert summary.safety_flags["network_calls"] is False
    assert summary.safety_flags["paper_trading"] is False
    joined = " ".join(summary.risk_notes)
    assert "defaulted to False" in joined
    assert "live_execution" in joined


# 7: Markdown enthält Experiment-Abschnitt.
def test_markdown_contains_experiment_section():
    md = summary_to_markdown(summarize_backtest_result(_sample_result()))
    assert "# Liquent Backtest Experiment" in md
    assert "## Experiment" in md
    assert "- ID:" in md
    assert "- Strategy:" in md


# 8: Markdown enthält Metrics-Tabelle.
def test_markdown_contains_metrics_table():
    md = summary_to_markdown(summarize_backtest_result(_sample_result()))
    assert "## Metrics" in md
    assert "| Metric | Value |" in md
    assert "| win_rate |" in md


# 9: Markdown enthält Risk Notes.
def test_markdown_contains_risk_notes():
    md = summary_to_markdown(summarize_backtest_result(_sample_result()))
    assert "## Risk Notes" in md
    assert "Risk Engine gate was applied before every simulated trade." in md
    assert "Rejected signals did not produce trades." in md


# 10: Markdown ist deterministisch bei gleichem Input.
def test_markdown_is_deterministic():
    md_a = summary_to_markdown(summarize_backtest_result(_sample_result()))
    md_b = summary_to_markdown(summarize_backtest_result(_sample_result()))
    assert md_a == md_b


# 11: Markdown/Reporting nutzt keine Wall-Clock-/aktuelle Uhrzeit.
def test_reporting_has_no_wall_clock_time():
    from liquent.backtesting import reporting

    source_code = inspect.getsource(reporting)
    for token in ("datetime.now", "time.time", "utcnow", "now()", "time.localtime"):
        assert token not in source_code, f"reporting darf {token!r} nicht nutzen"
    # Zusätzlich defensiv: aktueller Minuten-Zeitstempel kommt nicht im Output vor.
    md = summary_to_markdown(summarize_backtest_result(_sample_result()))
    now_minute = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
    assert now_minute not in md


# 12: Markdown enthält keine wertenden/empfehlenden Wörter.
def test_markdown_has_no_forbidden_words():
    md = summary_to_markdown(summarize_backtest_result(_sample_result())).lower()
    for word in ("profitabel", "garantiert", "live-trading starten", "trade this"):
        assert word not in md


# Zusatz: summary_to_dict liefert serialisierbare reine Datentypen.
def test_summary_to_dict_is_serializable():
    summary = summarize_backtest_result(_sample_result())
    as_dict = summary_to_dict(summary)
    assert isinstance(as_dict["risk_notes"], list)
    assert isinstance(as_dict["safety_flags"], dict)
    assert isinstance(as_dict["metrics"], dict)
    assert as_dict["experiment_id"] == summary.experiment_id
    # Darf nicht crashen (reine Datentypen; inf wird als Infinity serialisiert).
    json.dumps(as_dict)


# LQ-004 Phase 4: Reporting übernimmt die Risk-Sizing-Parameter aus dem Result.
def test_summary_carries_risk_sizing_parameters():
    summary = summarize_backtest_result(_sample_result())
    for key in (
        "sizing_mode", "risk_per_trade_pct", "max_position_notional",
        "max_daily_loss", "max_losing_streak",
    ):
        assert key in summary.parameters
    # Default-Lauf nutzt absolute (keine Default-Umstellung).
    assert summary.parameters["sizing_mode"] == "absolute"


# --------------------------------------------------------------------------- #
# LQ-004 Phase 5: modusabhängige Risk Notes (absolute / percent_risk / unknown)
# --------------------------------------------------------------------------- #
def _result_with_sizing(sizing_value=None, include_mode=True) -> BacktestResult:
    """Minimaler BacktestResult mit (optional) gesetztem sizing_mode."""
    params = {
        "strategy": "TestStrategy",
        "live_execution": False,
        "network_calls": False,
        "paper_trading": False,
    }
    if include_mode:
        params["sizing_mode"] = sizing_value
    return BacktestResult(
        experiment_id="lq004-test",
        number_of_trades=0,
        approved_signals=0,
        rejected_signals=0,
        starting_equity=0.0,
        ending_equity=0.0,
        equity_curve=(0.0,),
        metrics={"number_of_trades": 0},
        trades=(),
        parameters=params,
    )


# 1–3: percent_risk Risk Notes.
def test_percent_risk_risk_notes():
    summary = summarize_backtest_result(_result_with_sizing("percent_risk"))
    notes = summary.risk_notes
    assert "Percentage risk sizing was used." in notes
    assert "A stop_price is required for percent_risk sizing." in notes
    assert "Signals without stop_price are rejected by the Risk Engine." in notes
    assert "Risk Engine gate was applied before every simulated trade." in notes
    assert "Rejected signals did not produce trades." in notes


# 4: absolute Risk Notes.
def test_absolute_risk_notes():
    summary = summarize_backtest_result(_result_with_sizing("absolute"))
    notes = summary.risk_notes
    assert "Absolute sizing mode was used." in notes
    assert "Risk Engine gate was applied before every simulated trade." in notes
    assert "Rejected signals did not produce trades." in notes
    # Default-Sample-Lauf (absolute) trägt denselben Hinweis.
    assert "Absolute sizing mode was used." in summarize_backtest_result(_sample_result()).risk_notes


# 5: unbekannter sizing_mode -> defensive Audit Note.
def test_unknown_sizing_mode_defensive_note():
    summary = summarize_backtest_result(_result_with_sizing("martingale"))
    assert (
        "Sizing mode was missing or unknown; report uses defensive audit notes."
        in summary.risk_notes
    )


# 6: fehlender sizing_mode -> defensive Audit Note.
def test_missing_sizing_mode_defensive_note():
    summary = summarize_backtest_result(_result_with_sizing(include_mode=False))
    assert (
        "Sizing mode was missing or unknown; report uses defensive audit notes."
        in summary.risk_notes
    )


# 7: Safety Flags bleiben erhalten.
def test_safety_flags_preserved_with_sizing_modes():
    summary = summarize_backtest_result(_result_with_sizing("percent_risk"))
    assert summary.safety_flags == {
        "live_execution": False,
        "network_calls": False,
        "paper_trading": False,
    }


# 8: Markdown enthält die Risk-Notes-Sektion samt Modus-Hinweis.
def test_markdown_contains_percent_risk_notes():
    md = summary_to_markdown(summarize_backtest_result(_result_with_sizing("percent_risk")))
    assert "## Risk Notes" in md
    assert "Percentage risk sizing was used." in md
    assert "A stop_price is required for percent_risk sizing." in md


# 9: Markdown bleibt deterministisch (percent_risk).
def test_markdown_percent_risk_deterministic():
    a = summary_to_markdown(summarize_backtest_result(_result_with_sizing("percent_risk")))
    b = summary_to_markdown(summarize_backtest_result(_result_with_sizing("percent_risk")))
    assert a == b


# 10: keine wertenden/empfehlenden Wörter.
def test_markdown_modes_have_no_forbidden_words():
    forbidden = (
        "profitabel", "garantiert", "live-trading starten",
        "empfehlung kaufen", "sicherer gewinn", "trade this",
    )
    for mode_result in (
        _result_with_sizing("percent_risk"),
        _result_with_sizing("absolute"),
        _result_with_sizing("martingale"),
        _result_with_sizing(include_mode=False),
    ):
        md = summary_to_markdown(summarize_backtest_result(mode_result)).lower()
        for word in forbidden:
            assert word not in md


# LQ-003 Phase 3: Reporting übernimmt die Daten-Herkunfts-Metadaten.
def test_summary_carries_data_metadata_parameters():
    result = BacktestResult(
        experiment_id="lq003-test",
        number_of_trades=0,
        approved_signals=0,
        rejected_signals=0,
        starting_equity=0.0,
        ending_equity=0.0,
        equity_curve=(0.0,),
        metrics={"number_of_trades": 0},
        trades=(),
        parameters={
            "strategy": "TestStrategy",
            "sizing_mode": "absolute",
            "data_asset_class": "crypto",
            "data_exchange": "binance",
            "data_symbol": "BTCUSDT",
            "data_timeframe": "5m",
            "data_source_type": "local_csv",
        },
    )
    summary = summarize_backtest_result(result)
    assert summary.parameters["data_symbol"] == "BTCUSDT"
    assert summary.parameters["data_timeframe"] == "5m"
    assert summary.parameters["data_source_type"] == "local_csv"


# LQ-003 Phase 4: Reporting übernimmt die History-Report-Parameter.
def test_summary_carries_history_parameters():
    result = BacktestResult(
        experiment_id="lq003p4-test",
        number_of_trades=0,
        approved_signals=0,
        rejected_signals=0,
        starting_equity=0.0,
        ending_equity=0.0,
        equity_curve=(0.0,),
        metrics={"number_of_trades": 0},
        trades=(),
        parameters={
            "strategy": "TestStrategy",
            "sizing_mode": "absolute",
            "data_history_timeframe": "5m",
            "data_history_actual_bars": 3,
            "data_history_required_bars": 8640,
            "data_history_required_days": 30,
            "data_history_meets_minimum": False,
            "data_history_policy": "flag",
        },
    )
    summary = summarize_backtest_result(result)
    assert summary.parameters["data_history_timeframe"] == "5m"
    assert summary.parameters["data_history_required_bars"] == 8640
    assert summary.parameters["data_history_meets_minimum"] is False
    assert summary.parameters["data_history_policy"] == "flag"


# Zusatz: Summary hält keine mutable Defaults / ist frozen (immutable).
def test_summary_is_immutable():
    summary = summarize_backtest_result(_sample_result())
    raised = False
    try:
        summary.title = "anders"  # type: ignore[misc]
    except Exception:
        raised = True
    assert raised, "BacktestExperimentSummary muss frozen/immutable sein"
