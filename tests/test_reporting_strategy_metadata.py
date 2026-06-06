"""Tests für additive strategy_metadata im Reporting (LQ-011 Phase 2).

Zwei Ebenen:
- Reporting-Funktionen isoliert (deterministisch, ohne Datei/Netzwerk).
- CLI-Pfad über ``main(argv)`` + ``tmp_path`` (kein Artefakt außerhalb tmp_path).

Backward-Compat: ohne ``strategy_metadata`` bleibt der Output unverändert (kein
Strategy-Abschnitt, kein ``strategy``-Schlüssel im Dict). Keine echten Daten,
keine Reports committed, keine Netzwerk-/Live-/Paper-Trading-Pfade.
"""

from pathlib import Path

from liquent.backtesting.reporting import (
    summarize_backtest_result,
    summary_to_dict,
    summary_to_markdown,
)
from liquent.backtesting.runner import BacktestResult
from liquent.cli.backtest_mid_breakout import main

_FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return str(_FIXTURES / name)


def _cli_args(output: Path, *extra: str) -> list[str]:
    return [
        "--csv", _fixture("strategy_mid_breakout_long.csv"),
        "--output", str(output),
        "--symbol", "TESTUSDT",
        "--exchange", "synthetic",
        "--asset-class", "crypto",
        *extra,
    ]


def _bare_result() -> BacktestResult:
    """Minimaler, deterministischer BacktestResult (keine Datenquelle nötig)."""
    return BacktestResult(
        experiment_id="lq011-test",
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


_V0_META = {
    "family": "mid_breakout",
    "key": "v0",
    "name": "MidBreakoutStrategy",
    "params": {
        "lookback_bars": 3,
        "stop_distance_pct": 0.05,
        "allow_short": True,
        "min_strength": 0.0,
    },
}
_V1_META = {
    "family": "mid_breakout",
    "key": "v1",
    "name": "MidBreakoutStrategyV1",
    "params": {
        "lookback_bars": 12,
        "stop_distance_pct": 0.01,
        "breakout_threshold_pct": 0.001,
        "cooldown_bars": 3,
        "allow_short": True,
        "min_strength": 0.0,
    },
}


# --------------------------------------------------------------------------- #
# Reporting-Ebene (isoliert)
# --------------------------------------------------------------------------- #


# 1: Ohne metadata -> backward-compatible (kein Strategy-Abschnitt, kein Key).
def test_no_metadata_is_backward_compatible():
    summary = summarize_backtest_result(_bare_result())
    assert summary.strategy_metadata is None
    md = summary_to_markdown(summary)
    assert "## Strategy" not in md
    assert "### Strategy Parameters" not in md
    assert "strategy" not in summary_to_dict(summary)


# 2: v0-metadata -> Markdown + Dict enthalten v0-Felder, keine v1-only Parameter.
def test_v0_metadata_in_report():
    summary = summarize_backtest_result(_bare_result(), strategy_metadata=_V0_META)
    md = summary_to_markdown(summary)
    assert "## Strategy" in md
    assert "| key | v0 |" in md
    assert "| name | MidBreakoutStrategy |" in md
    for token in ("lookback_bars", "stop_distance_pct", "allow_short", "min_strength"):
        assert f"| {token} |" in md
    # keine v1-only Parameter im v0-Report.
    assert "breakout_threshold_pct" not in md
    assert "cooldown_bars" not in md
    as_dict = summary_to_dict(summary)
    assert as_dict["strategy"]["key"] == "v0"
    assert as_dict["strategy"]["name"] == "MidBreakoutStrategy"
    assert "breakout_threshold_pct" not in as_dict["strategy"]["params"]


# 3: v1-metadata -> Markdown + Dict enthalten v1-Felder inkl. v1-only Parameter.
def test_v1_metadata_in_report():
    summary = summarize_backtest_result(_bare_result(), strategy_metadata=_V1_META)
    md = summary_to_markdown(summary)
    assert "| key | v1 |" in md
    assert "| name | MidBreakoutStrategyV1 |" in md
    for token in (
        "lookback_bars", "stop_distance_pct", "breakout_threshold_pct",
        "cooldown_bars", "allow_short", "min_strength",
    ):
        assert f"| {token} |" in md
    as_dict = summary_to_dict(summary)
    assert as_dict["strategy"]["key"] == "v1"
    assert as_dict["strategy"]["params"]["breakout_threshold_pct"] == 0.001
    assert as_dict["strategy"]["params"]["cooldown_bars"] == 3


# 4: Determinismus -> gleiche Eingaben liefern byte-identisches Markdown.
def test_markdown_with_metadata_is_deterministic():
    a = summary_to_markdown(summarize_backtest_result(_bare_result(), strategy_metadata=_V1_META))
    b = summary_to_markdown(summarize_backtest_result(_bare_result(), strategy_metadata=_V1_META))
    assert a == b


# 5: Feldreihenfolge wird normalisiert (family, key, name), unabhängig vom Input.
def test_metadata_field_order_normalized():
    shuffled = {"name": "MidBreakoutStrategyV1", "params": {}, "key": "v1", "family": "mid_breakout"}
    summary = summarize_backtest_result(_bare_result(), strategy_metadata=shuffled)
    md = summary_to_markdown(summary)
    i_family = md.index("| family |")
    i_key = md.index("| key |")
    i_name = md.index("| name |")
    assert i_family < i_key < i_name


# --------------------------------------------------------------------------- #
# CLI-Ebene (main + tmp_path)
# --------------------------------------------------------------------------- #


# 6: CLI v0 (Default) -> Report enthält v0-Strategy-Abschnitt mit v0-Defaults.
def test_cli_v0_report_contains_strategy_section(tmp_path):
    out = tmp_path / "v0.md"
    assert main(_cli_args(out)) == 0
    text = out.read_text(encoding="utf-8")
    assert "## Strategy" in text
    assert "| key | v0 |" in text
    assert "| name | MidBreakoutStrategy |" in text
    assert "| lookback_bars | 3 |" in text
    assert "| stop_distance_pct | 0.05 |" in text
    assert "breakout_threshold_pct" not in text


# 7: CLI v1 ohne Parameter -> effektive v1-Defaults im Report.
def test_cli_v1_report_contains_resolved_defaults(tmp_path):
    out = tmp_path / "v1.md"
    assert main(_cli_args(out, "--strategy", "v1")) == 0
    text = out.read_text(encoding="utf-8")
    assert "| key | v1 |" in text
    assert "| name | MidBreakoutStrategyV1 |" in text
    assert "| lookback_bars | 12 |" in text
    assert "| stop_distance_pct | 0.01 |" in text
    assert "| breakout_threshold_pct | 0.001 |" in text
    assert "| cooldown_bars | 3 |" in text


# 8: CLI v1 mit Overrides -> explizit gesetzte Werte erscheinen im Report.
def test_cli_v1_report_reflects_overrides(tmp_path):
    out = tmp_path / "v1o.md"
    rc = main(_cli_args(
        out, "--strategy", "v1",
        "--lookback-bars", "20",
        "--stop-distance-pct", "0.02",
        "--breakout-threshold-pct", "0.005",
        "--cooldown-bars", "7",
    ))
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert "| lookback_bars | 20 |" in text
    assert "| stop_distance_pct | 0.02 |" in text
    assert "| breakout_threshold_pct | 0.005 |" in text
    assert "| cooldown_bars | 7 |" in text


# 9: Statischer Scan -> Reporting-Modul ohne Netzwerk-/Live-/Exchange-Pfade.
#     Hinweis: "paper_trading"/"live_execution"/"network_calls" sind im Reporting
#     legitime Safety-FLAG-Namen (sie dokumentieren deren Abwesenheit) und daher
#     bewusst NICHT in der Verbotsliste.
def test_reporting_module_has_no_forbidden_paths():
    import inspect

    from liquent.backtesting import reporting as module

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
    ]
    for token in forbidden:
        assert token not in source_code, f"Reporting-Modul darf {token!r} nicht enthalten"
