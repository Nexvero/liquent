"""Safe customer evidence projection in the existing authenticated job view."""
from copy import deepcopy

import pytest

from liquent_platform.transport.http.research_results import result_document


def pilot():
    return {"pilot_result": {"schema": "liquent.research-pilot.result.v1", "variants": [
        {"variant_id": name, "input_fingerprint": "sha256:bound-" + name,
         "status": state, "inputs": {"strategy": "mid-breakout-v1",
             "strategy_parameters": {"lookback": 3, "allow_short": False},
             "costs": {"fee_rate": .001, "spread": .2, "slippage": .0005},
             "risk": {"sizing_mode": "percent_risk", "risk_per_trade_pct": .01}},
         "summary": ({"number_of_trades": count, "ending_equity": 1234,
                      "parameters": {"sizing_mode": "percent_risk"}}
                     if state != "failed" else None),
         "evidence": {"cost_totals": {"gross_pnl": 15, "net_pnl": 10, "fee": 2,
                         "spread": 1, "slippage": 2, "total": 5},
                      "effective_risk": {"max_daily_loss": "Kein wirksamer Verlustschutz"}},
         "error": "Synthetic failure" if state == "failed" else None}
        for name, state, count in (("Z-first", "succeeded", 2), ("A-second", "no_signals", 0),
                                   ("M-third", "failed", None))]}}


def test_order_partial_failure_inputs_costs_and_binding():
    document = result_document("job-1", "succeeded", pilot())
    assert document.index("Variante: Z-first") < document.index("Variante: A-second") < document.index("Variante: M-third")
    for text in ("Keine Signale", "Fehlgeschlagen", "Synthetic failure", "Keine Ergebniszusammenfassung",
                 "sha256:bound-Z-first", "lookback", "Bruttoergebnis", "Nettoergebnis", "15,00",
                 "Gebühren", "Slippage-Kosten", "Kein wirksamer Verlustschutz", "kein Ranking",
                 "Ohne Trades", "/v1/research/jobs/job-1/evidence"):
        assert text in document


@pytest.mark.parametrize("status", ["succeeded", "failed", "queued", "unknown"])
def test_limits_prominent_even_without_results(status):
    document = result_document("job", status, None)
    assert "nach einem Datenbalken" in document
    assert "keine tatsächliche Stop-Loss-Ausführung" in document
    assert "Mittelkurs-Proxy" in document


def test_legacy_summary_compatible_and_no_estimated_pnl():
    document = result_document("old", "succeeded", {
        "starting_equity": 1000, "ending_equity": 1234,
        "parameters": {"fee_rate": .001, "sizing_mode": "absolute", "data_source_path": "private-path"},
        "cost_metadata": {"spread": .2}, "strategy_metadata": {"lookback": 5, "token": "secret"}})
    assert "1.234,00" in document and "fee_rate" in document and "lookback" in document
    assert "private-path" not in document and "secret" not in document
    assert "Bruttoergebnis</dt><dd>Nicht verfügbar" in document
    assert "Nettoergebnis</dt><dd>Nicht verfügbar" in document


def test_untrusted_nested_metadata_and_job_path_are_escaped():
    evidence = pilot()
    variant = evidence["pilot_result"]["variants"][0]
    variant["variant_id"] = '<script>alert(1)</script>'
    variant["inputs"]["hypothesis"] = '<img src=x onerror=alert(1)>'
    variant["evidence"]["effective_risk"]["max_daily_loss"] = '<svg onload=alert(1)>'
    variant["inputs"]["unknown"] = "private-secret"
    variant["status"] = ["succeeded"]
    document = result_document('a/"?b', "succeeded", evidence)
    assert '<script>' not in document and '<img src=x' not in document and '<svg onload' not in document
    assert "&lt;script&gt;" in document and "private-secret" not in document
    assert "a%2F%22%3Fb/evidence" in document
    assert "Status nicht verfügbar" in document


@pytest.mark.parametrize("value", [None, True, float("nan"), float("inf"), "10", {}, 10**1000])
def test_missing_or_non_numeric_costs_never_render_zero(value):
    evidence = pilot()
    evidence["pilot_result"]["variants"][0]["evidence"]["cost_totals"]["gross_pnl"] = value
    document = result_document("job", "succeeded", evidence)
    assert "Bruttoergebnis</dt><dd>Nicht verfügbar" in document


@pytest.mark.parametrize("variants", [None, {}, [], [{"status": "succeeded"}], [None]*3])
def test_invalid_variant_structure_fails_closed(variants):
    evidence = pilot()
    evidence["pilot_result"]["variants"] = variants
    assert "Varianten-Evidenz unvollständig" in result_document("job", "succeeded", evidence)


def test_unknown_schema_not_projected_and_projection_does_not_mutate():
    evidence = pilot()
    original = deepcopy(evidence)
    result_document("job", "succeeded", evidence)
    assert evidence == original
    evidence["pilot_result"]["schema"] = "unknown"
    document = result_document("job", "succeeded", evidence)
    assert "nicht unterstützt" in document and "Z-first" not in document


def test_existing_serialized_summary_shape_and_dataset_identity():
    evidence = pilot()
    variant = evidence["pilot_result"]["variants"][0]
    variant["inputs"].update(dataset_fingerprint="sha256:dataset", timeframe="5m")
    variant["summary"].update(cost_model={"fee_rate": .003},
                              strategy={"params": {"lookback_bars": 7}})
    document = result_document("job", "succeeded", evidence)
    assert "lookback_bars" in document and "sha256:dataset" in document and "5m" in document
    assert "fee_rate</th><td>0.003" in document
