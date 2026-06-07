"""LQ-043 — ergänzende Reporting-/Comparison-Regressionstests.

Diese Tests schreiben ausschließlich das BESTEHENDE Verhalten von
``src/liquent/backtesting/reporting.py`` und
``src/liquent/backtesting/comparison_reporting.py`` fest (Behavior-Lock). Keine
Produktionslogik-Änderung, keine neuen Features, keine Änderung bestehender
Reporting-/Comparison-Tests.

Abgedeckt werden bisher nicht explizit gesicherte Konventionen/Grenzwerte
(siehe ``docs/lq-043-reporting-comparison-stabilization.md``, Test Plan):
Reporting-Fallbacks/Defensivkopien/Output-Reihenfolge sowie Comparison-
Normalisierungs-Guards. Reihenfolgen sind rein technische Output-Contracts —
KEINE Bewertung, KEIN Ranking, KEINE Empfehlung.
"""

from liquent.backtesting.comparison_reporting import normalize_comparison
from liquent.backtesting.reporting import (
    summarize_backtest_result,
    summary_to_dict,
    summary_to_markdown,
)
from liquent.backtesting.runner import BacktestResult


def _result(parameters: dict) -> BacktestResult:
    """Minimaler, deterministischer BacktestResult (kein Runner-Lauf, kein I/O)."""
    return BacktestResult(
        experiment_id="lq043-test",
        number_of_trades=0,
        approved_signals=0,
        rejected_signals=0,
        starting_equity=0.0,
        ending_equity=0.0,
        equity_curve=(0.0,),
        metrics={"number_of_trades": 0},
        trades=(),
        parameters=parameters,
    )


# --------------------------------------------------------------------------- #
# reporting.py
# --------------------------------------------------------------------------- #
def test_strategy_name_falls_back_to_unknown():
    summary = summarize_backtest_result(_result({"sizing_mode": "absolute"}))
    assert summary.strategy_name == "unknown"


def test_not_investment_advice_note_in_all_sizing_modes():
    advice = "Descriptive summary only; this is not investment advice."
    for params in (
        {"strategy": "S", "sizing_mode": "percent_risk"},
        {"strategy": "S", "sizing_mode": "absolute"},
        {"strategy": "S", "sizing_mode": "martingale"},  # unbekannt
        {"strategy": "S"},  # fehlend
    ):
        notes = summarize_backtest_result(_result(params)).risk_notes
        assert advice in notes, f"advice-Note fehlt fuer {params!r}"


def test_strategy_metadata_non_dict_params_normalized_to_empty():
    meta = {"family": "f", "key": "k", "name": "n", "params": "not-a-dict"}
    summary = summarize_backtest_result(
        _result({"strategy": "S", "sizing_mode": "absolute"}), strategy_metadata=meta
    )
    assert summary.strategy_metadata is not None
    assert summary.strategy_metadata["params"] == {}


def test_markdown_full_section_order_with_metadata():
    summary = summarize_backtest_result(
        _result({"strategy": "S", "sizing_mode": "absolute",
                 "live_execution": False, "network_calls": False, "paper_trading": False}),
        strategy_metadata={"family": "f", "key": "k", "name": "n", "params": {}},
        cost_metadata={"fee_rate": 0.0, "spread": 0.0, "slippage": 0.0},
    )
    md = summary_to_markdown(summary)
    order = [
        "## Experiment",
        "## Strategy",
        "## Cost Model",
        "## Metrics",
        "## Parameters",
        "## Risk Notes",
        "## Safety Flags",
    ]
    positions = [md.index(section) for section in order]
    assert positions == sorted(positions), f"Abschnittsreihenfolge nicht stabil: {positions}"


def test_summary_uses_defensive_copies_of_result():
    params = {"strategy": "S", "sizing_mode": "absolute", "seed": 7}
    result = _result(params)
    summary = summarize_backtest_result(result)
    # Nachtraegliche Mutation des (mutable) Result-Dicts darf die Summary nicht aendern.
    result.parameters["seed"] = 999
    result.metrics["number_of_trades"] = 123
    assert summary.parameters["seed"] == 7
    assert summary.metrics["number_of_trades"] == 0


def test_markdown_formats_bool_as_words_not_digits():
    summary = summarize_backtest_result(
        _result({"strategy": "S", "sizing_mode": "absolute",
                 "live_execution": False, "network_calls": False, "paper_trading": False})
    )
    md = summary_to_markdown(summary)
    assert "| live_execution | False |" in md
    assert "| live_execution | 0 |" not in md


# --------------------------------------------------------------------------- #
# comparison_reporting.py
# --------------------------------------------------------------------------- #
def test_variants_as_str_treated_as_no_variants():
    assert normalize_comparison({"variants": "abc"})["variants"] == []
    assert normalize_comparison({"variants": 5})["variants"] == []


def test_custom_notes_override_default_notes():
    notes = normalize_comparison({"notes": ["Custom note."]})["notes"]
    assert notes == ["Custom note."]
    assert "Synthetic data only." not in notes


def test_non_sequence_notes_fall_back_to_default_notes():
    for bad in (123, "hello"):
        notes = normalize_comparison({"notes": bad})["notes"]
        assert "Synthetic data only." in notes
        assert "No profitability assessment." in notes
        assert "No trading recommendation." in notes


def test_strategy_params_non_mapping_normalized_to_empty():
    norm = normalize_comparison({"variants": [{"strategy": {"family": "f", "params": "x"}}]})
    assert norm["variants"][0]["strategy"]["params"] == {}
