"""Tests für additive cost_metadata im Reporting (LQ-012 Phase 2).

Spiegelt das ``strategy_metadata``-Muster (LQ-011). Backward-Compat: ohne
``cost_metadata`` bleibt der Output unverändert (kein ``## Cost Model``-Abschnitt,
kein ``cost_model``-Schlüssel im Dict). Keine echten Daten, keine Reports
committed, keine Netzwerk-/Live-/Paper-Trading-Pfade.
"""

from liquent.backtesting.reporting import (
    summarize_backtest_result,
    summary_to_dict,
    summary_to_markdown,
)
from liquent.backtesting.runner import BacktestResult


def _bare_result() -> BacktestResult:
    return BacktestResult(
        experiment_id="lq012-test",
        number_of_trades=0,
        approved_signals=0,
        rejected_signals=0,
        starting_equity=10_000.0,
        ending_equity=10_000.0,
        equity_curve=(10_000.0,),
        metrics={"number_of_trades": 0},
        trades=(),
        parameters={
            "strategy": "MidBreakoutStrategyV1",
            "sizing_mode": "percent_risk",
            "live_execution": False,
            "network_calls": False,
            "paper_trading": False,
        },
    )


_COST = {"fee_rate": 0.001, "spread": 0.05, "slippage": 0.0005}
_STRAT = {
    "family": "mid_breakout",
    "key": "v1",
    "name": "MidBreakoutStrategyV1",
    "params": {"lookback_bars": 12, "stop_distance_pct": 0.01},
}


# 1: Ohne cost_metadata -> backward-compatible (kein Abschnitt, kein Key).
def test_no_cost_metadata_is_backward_compatible():
    summary = summarize_backtest_result(_bare_result())
    assert summary.cost_metadata is None
    md = summary_to_markdown(summary)
    assert "## Cost Model" not in md
    assert "cost_model" not in summary_to_dict(summary)


# 2: Mit cost_metadata -> Markdown + Dict enthalten fee_rate/spread/slippage.
def test_cost_metadata_in_report():
    summary = summarize_backtest_result(_bare_result(), cost_metadata=_COST)
    md = summary_to_markdown(summary)
    assert "## Cost Model" in md
    assert "| fee_rate | 0.001 |" in md
    assert "| spread | 0.05 |" in md
    assert "| slippage | 0.0005 |" in md
    as_dict = summary_to_dict(summary)
    assert as_dict["cost_model"] == {"fee_rate": 0.001, "spread": 0.05, "slippage": 0.0005}


# 3: Defaults 0.0 werden explizit ausgewiesen (auch frictionless ist dokumentiert).
def test_cost_metadata_zero_is_explicit():
    summary = summarize_backtest_result(
        _bare_result(), cost_metadata={"fee_rate": 0.0, "spread": 0.0, "slippage": 0.0}
    )
    md = summary_to_markdown(summary)
    assert "## Cost Model" in md
    assert "| fee_rate | 0.0 |" in md
    assert "| spread | 0.0 |" in md
    assert "| slippage | 0.0 |" in md


# 4: strategy_metadata + cost_metadata gemeinsam -> beide Abschnitte, deterministische Reihenfolge.
def test_strategy_and_cost_metadata_together():
    summary = summarize_backtest_result(
        _bare_result(), strategy_metadata=_STRAT, cost_metadata=_COST
    )
    md = summary_to_markdown(summary)
    assert "## Strategy" in md
    assert "## Cost Model" in md
    # Reihenfolge: Experiment -> Strategy -> Cost Model -> Metrics.
    assert md.index("## Strategy") < md.index("## Cost Model") < md.index("## Metrics")
    as_dict = summary_to_dict(summary)
    assert "strategy" in as_dict
    assert "cost_model" in as_dict


# 5: Feldreihenfolge normalisiert (fee_rate, spread, slippage), unabhängig vom Input.
def test_cost_field_order_normalized():
    shuffled = {"slippage": 0.0005, "fee_rate": 0.001, "spread": 0.05}
    md = summary_to_markdown(summarize_backtest_result(_bare_result(), cost_metadata=shuffled))
    i_fee = md.index("| fee_rate |")
    i_spread = md.index("| spread |")
    i_slip = md.index("| slippage |")
    assert i_fee < i_spread < i_slip


# 6: Fehlende Cost-Felder werden defensiv auf 0.0 gesetzt.
def test_cost_metadata_missing_fields_default_zero():
    as_dict = summary_to_dict(
        summarize_backtest_result(_bare_result(), cost_metadata={"fee_rate": 0.002})
    )
    assert as_dict["cost_model"] == {"fee_rate": 0.002, "spread": 0.0, "slippage": 0.0}


# 7: Determinismus -> gleiche Eingaben liefern byte-identisches Markdown.
def test_markdown_with_cost_metadata_is_deterministic():
    a = summary_to_markdown(summarize_backtest_result(_bare_result(), cost_metadata=_COST))
    b = summary_to_markdown(summarize_backtest_result(_bare_result(), cost_metadata=_COST))
    assert a == b
