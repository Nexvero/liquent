"""Customer report projections preserve evidence and never execute research."""

from copy import deepcopy
from dataclasses import asdict, replace
import json
import math

import pytest

from liquent.backtesting.metrics import TradeResult
from liquent.backtesting.reporting import summarize_backtest_result, summary_to_dict
from liquent.backtesting.runner import BacktestResult
from liquent.research_pilot.contracts import MODEL_LIMITS, RESULT_SCHEMA, PilotResult, VariantResult
from liquent.research_pilot.customer_report import pilot_to_dict, pilot_to_markdown


def _variant(variant_id="z-first", status="succeeded", *, trades=True, rejected=0):
    trade = TradeResult(100, 103, 2, "long", gross_pnl=6, costs=1.25,
                        net_pnl=4.75, r_multiple=2.375, duration_bars=1,
                        entry_time="2026-01-01T00:00:00Z", exit_time="2026-01-01T00:05:00Z")
    backend = BacktestResult(
        experiment_id="experiment-exact", number_of_trades=int(trades),
        approved_signals=int(trades), rejected_signals=rejected,
        starting_equity=1000, ending_equity=1004.75 if trades else 1000,
        equity_curve=(1000, 1004.75) if trades else (1000,),
        metrics={"profit_factor": math.inf if trades else 0.0, "win_rate": 1.0 if trades else 0.0},
        trades=(trade,) if trades else (),
        parameters={"strategy": "Breakout", "sizing_mode": "percent_risk",
                    "fee_rate": .001, "spread": .2, "slippage": .0005,
                    "live_execution": False, "network_calls": False, "paper_trading": False},
    )
    summary = summarize_backtest_result(
        backend, title="Kundentest", strategy_metadata={"family": "breakout", "key": "mid", "name": "Breakout", "params": {"lookback": 3}},
        cost_metadata={"fee_rate": .001, "spread": .2, "slippage": .0005},
    )
    evidence = {
        "effective_risk": {"max_daily_loss": "Nicht wirksam: day_realized_loss bleibt 0",
                           "stop_price": "Nur Positionsgröße, kein Stop-Ausstieg"},
        "runner_parameters": deepcopy(backend.parameters),
        "trades": [asdict(t) for t in backend.trades],
        "equity_curve": list(backend.equity_curve),
        "cost_totals": {"fee": .4, "spread": .6, "slippage": .25,
                        "total": 1.25, "gross_pnl": 6, "net_pnl": 4.75} if trades else {
                            key: 0 for key in ("fee", "spread", "slippage", "total", "gross_pnl", "net_pnl")},
        "metric_notes": {"r_multiple": "net_pnl / quantity, kein stopbasiertes R"},
    }
    if status in ("failed", "blocked_data"):
        summary, evidence = None, None
    return VariantResult(variant_id, "input-exact-123", status,
                         {"variant_id": variant_id, "strategy": {"lookback": 3},
                          "risk": {"max_daily_loss": 100}, "costs": {"fee_rate": .001, "spread": .2, "slippage": .0005},
                          "dataset_fingerprint": "dataset-exact-456", "timeframe": "5m"},
                         summary, evidence, "Daten ungültig" if status == "blocked_data" else
                         "Runner fehlgeschlagen" if status == "failed" else None)


def _pilot(*variants):
    return PilotResult("pilot-exact-789", {
        "reference": "Auftrag-42", "title": "Kundenprüfung", "instrument": "BTCUSD",
        "price_unit": "USD", "data_origin": "Lokale CSV des Kunden",
        "assumptions": ["Keine Brokeranbindung", "Unveränderte OHLCV-Daten"],
    }, {
        "status": "valid", "dataset_fingerprint": "dataset-exact-456", "rows": 12,
        "period_start": "2026-01-01T00:00:00Z", "period_end": "2026-01-01T00:55:00Z",
        "timeframe": "5m", "interval_seconds": 300, "issues": [], "gaps": [],
        "history": {"meets_minimum": False}, "warnings": ["Kurze Historie"],
    }, tuple(variants), {"python": "3.12.9", "implementation_fingerprint": "implementation-exact",
                         "code_scope": ["runner.py", "customer_report.py"]},
       {"schema": "liquent.research-pilot.config.v1", "variants": [v.inputs for v in variants],
        "history_policy": "flag", "starting_equity": 1000})


def test_schema_exact_ids_costs_and_complete_inputs():
    variant = _variant()
    report = pilot_to_dict(_pilot(variant))
    assert set(report) == {"schema", "pilot_id", "order", "data_quality", "variants", "runtime", "configuration", "model_limits"}
    assert report["schema"] == RESULT_SCHEMA
    assert report["pilot_id"] == "pilot-exact-789"
    item = report["variants"][0]
    assert set(item) == {"variant_id", "input_fingerprint", "status", "inputs", "summary", "evidence", "error"}
    assert item["variant_id"] == "z-first"
    assert item["input_fingerprint"] == "input-exact-123"
    assert item["inputs"] == variant.inputs
    assert item["evidence"]["cost_totals"] == variant.evidence["cost_totals"]
    assert item["evidence"]["trades"] == variant.evidence["trades"]
    assert item["evidence"]["equity_curve"] == variant.evidence["equity_curve"]
    assert item["summary"]["experiment_id"] == "experiment-exact"
    expected = summary_to_dict(variant.summary)
    expected["metrics"]["profit_factor"] = None
    assert item["summary"] == expected
    assert report["model_limits"] == list(MODEL_LIMITS)
    json.dumps(report, allow_nan=False)
    markdown = pilot_to_markdown(_pilot(variant))
    assert "| fee_rate | 0.001 |" in markdown
    assert "| spread | 0.2 |" in markdown
    assert "| slippage | 0.0005 |" in markdown
    assert "| fee_rate | 0.0 |" not in markdown


@pytest.mark.parametrize("status", ["succeeded", "no_signals", "failed", "blocked_data"])
def test_representative_outcomes(status):
    variant = _variant(status=status, trades=status != "no_signals")
    result = _pilot(variant)
    item = pilot_to_dict(result)["variants"][0]
    md = pilot_to_markdown(result)
    assert item["status"] == status
    assert status.replace("_", "&#95;") in md
    if status in ("failed", "blocked_data"):
        assert item["summary"] is None
        assert item["evidence"] is None
        assert "nicht bestanden" in md
        assert "Keine Ergebniszusammenfassung" in md
        assert "Nicht vorhanden | Nicht vorhanden | Nicht vorhanden" in md
    elif status == "no_signals":
        assert item["summary"]["metrics"]["win_rate"] == 0.0
        assert "Nicht aussagekräftig: keine Trades" in md
        assert "| win&#95;rate | 0.0 |" not in md
        assert "Keine Signale" in md


def test_no_signals_is_distinct_from_rejected_and_failed_partial_results():
    rejected = _variant("rejected", trades=False, rejected=4)
    failed_partial = replace(_variant("partial"), status="failed", error="Abbruch nach Trade")
    blocked = _variant("blocked", "blocked_data")
    result = _pilot(rejected, failed_partial, blocked)
    report = pilot_to_dict(result)
    assert report["variants"][0]["summary"]["rejected_signals"] == 4
    assert report["variants"][1]["evidence"]["trades"]
    md = pilot_to_markdown(result)
    assert "Keine Signale (no_signals)" not in md
    assert "Vorhandene Teilergebnisse" in md
    assert "Abbruch nach Trade" in md
    assert "Nicht ausgeführt" in md


def test_strict_json_recurses_and_explains_non_finite_values():
    variant = _variant()
    variant.inputs["nested"] = {"values": [math.nan, -math.inf, {"x": math.inf}]}
    variant.evidence["runner_parameters"]["nested"] = {"nan": math.nan}
    result = _pilot(variant)
    report = pilot_to_dict(result)
    item = report["variants"][0]
    assert item["inputs"]["nested"]["values"] == [None, None, {"x": None}]
    assert item["evidence"]["runner_parameters"]["nested"]["nan"] is None
    assert item["summary"]["metrics"]["profit_factor"] is None
    notes = item["evidence"]["metric_notes"]
    assert "Gewinnen ohne Verluste" in notes["variant.summary.metrics.profit_factor"]
    assert "variant.inputs.nested.values[2].x" in notes
    assert notes["r_multiple"] == variant.evidence["metric_notes"]["r_multiple"]
    json.dumps(report, allow_nan=False)
    assert "nicht endlich" in pilot_to_markdown(result)


def test_non_finite_envelope_parameters_explained_even_without_variants():
    result = _pilot()
    result.configuration["nested"] = {"values": [math.inf, math.nan]}
    report = pilot_to_dict(result)
    assert report["configuration"]["nested"]["values"] == [None, None]
    assert "result.configuration.nested.values[0]" in report["data_quality"]["warnings"][-2]
    json.dumps(report, allow_nan=False)
    assert "Berichtsserialisierung" in pilot_to_markdown(result)


def test_malicious_metadata_cannot_forge_headings_tables_or_html():
    attack = 'owned|column\n# FORGED\r\n<script>alert(1)</script> [click](javascript:alert(1)) `code` \'quote\''
    variant = _variant(attack)
    variant = replace(variant, input_fingerprint=attack, error=attack,
                      summary=replace(variant.summary, experiment_id=attack, title=attack,
                                      strategy_name=attack, parameters={attack: attack},
                                      strategy_metadata={"name": attack, "params": {attack: attack}},
                                      risk_notes=(attack,)))
    variant.inputs[attack] = {"nested": attack}
    variant.evidence["metric_notes"][attack] = attack
    result = _pilot(variant)
    result.order["title"] = attack
    result.order["assumptions"] = [attack]
    result.data_quality["warnings"] = [attack]
    result.runtime["python"] = attack
    result.configuration[attack] = attack
    md = pilot_to_markdown(result)
    assert "<script>" not in md
    assert "\n# FORGED" not in md
    assert "owned|column" not in md
    assert "[click](javascript:" not in md
    assert "&#124;" in md
    assert "&lt;script&gt;" in md
    assert "&#x27;quote&#x27;" in md
    assert pilot_to_dict(result)["order"]["title"] == attack


def test_order_model_limits_units_and_repetition_are_visible():
    result = _pilot(_variant("z-first"), _variant("a-second", "failed"),
                    _variant("m-third", "no_signals", trades=False))
    md = pilot_to_markdown(result)
    assert [v["variant_id"] for v in pilot_to_dict(result)["variants"]] == ["z-first", "a-second", "m-third"]
    assert md.index("### Variante: z-first") < md.index("### Variante: a-second") < md.index("### Variante: m-third")
    for limit in MODEL_LIMITS:
        assert limit in md
    for text in ("USD", "Auftrag-42", "Kurze Historie", "Wirksames Risiko", "0.001 = 0.1 %",
                 "absoluter Preisaufschlag pro Einheit", "Einstieg und Ausstieg", "Wiederholung",
                 "implementation-exact", "dataset-exact-456", "Lokale CSV des Kunden"):
        assert text in md
    assert "690" not in md


def test_deterministic_defensive_copy_and_no_mutation():
    result = _pilot(_variant(), _variant("empty", "no_signals", trades=False))
    before = deepcopy(result)
    first = pilot_to_dict(result)
    assert first == pilot_to_dict(result)
    assert pilot_to_markdown(result) == pilot_to_markdown(result)
    assert result == before
    first["variants"][0]["evidence"]["trades"][0]["net_pnl"] = 99
    first["configuration"]["variants"][0]["strategy"]["lookback"] = 99
    assert result == before


def test_empty_blocked_pilot_does_not_fabricate_variants():
    result = _pilot()
    result.data_quality["status"] = "invalid"
    result.data_quality["issues"] = ["Keine Daten"]
    assert pilot_to_dict(result)["variants"] == []
    assert "Keine Daten" in pilot_to_markdown(result)
    assert "| variant_0" not in pilot_to_markdown(result)


def test_reporting_does_not_access_files_or_network(monkeypatch):
    import builtins
    import socket
    from pathlib import Path

    result = _pilot(_variant())

    def forbidden(*args, **kwargs):
        raise AssertionError("Reporting must not perform I/O")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    assert pilot_to_dict(result)["pilot_id"] == result.pilot_id
    assert "Kundenbericht" in pilot_to_markdown(result)
