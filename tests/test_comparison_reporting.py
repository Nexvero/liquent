"""Tests für comparison_reporting (LQ-013 Phase 2).

Rein deterministische String-/Dict-Assertions — KEINE Dateien, kein Netzwerk,
keine Reports, keine Echtdaten. Prüft den strukturierten synthetischen
Vergleichsreport (deskriptiv, keine Bewertung/Empfehlung).
"""

from liquent.backtesting.comparison_reporting import (
    normalize_comparison,
    render_comparison_markdown,
)


def _comparison() -> dict:
    return {
        "title": "Synthetic Strategy Comparison",
        "dataset": {
            "name": "micro_breakout_long",
            "type": "synthetic",
            "bars": 18,
            "description": "Sideways phase, micro breakout, real breakout",
        },
        "variants": [
            {
                "label": "v0",
                "strategy": {
                    "family": "mid_breakout",
                    "key": "v0",
                    "name": "MidBreakoutStrategy",
                    "params": {
                        "lookback_bars": 3,
                        "stop_distance_pct": 0.05,
                        "allow_short": True,
                        "min_strength": 0.0,
                    },
                },
                "cost_model": {"fee_rate": 0.0, "spread": 0.0, "slippage": 0.0},
                "technical_results": {
                    "signals_total": 2,
                    "trades_total": 2,
                    "approved_signals": 2,
                    "rejected_signals": 0,
                },
            },
            {
                "label": "v1",
                "strategy": {
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
                },
                "cost_model": {"fee_rate": 0.001, "spread": 0.0, "slippage": 0.0},
                "technical_results": {
                    "signals_total": 1,
                    "trades_total": 1,
                    "approved_signals": 1,
                    "rejected_signals": 0,
                },
            },
        ],
    }


# 1: Dataset-Abschnitt wird gerendert.
def test_renders_dataset_section():
    md = render_comparison_markdown(_comparison())
    assert "# Synthetic Strategy Comparison" in md
    assert "## Dataset" in md
    assert "| name | micro_breakout_long |" in md
    assert "| type | synthetic |" in md
    assert "| bars | 18 |" in md
    assert "| description | Sideways phase, micro breakout, real breakout |" in md


# 2: Varianten-Tabelle enthält v0 und v1.
def test_variants_table_contains_v0_and_v1():
    md = render_comparison_markdown(_comparison())
    assert "## Variants" in md
    assert "| Variant | Strategy | Signals | Trades | Approved | Rejected |" in md
    assert "| v0 | MidBreakoutStrategy | 2 | 2 | 2 | 0 |" in md
    assert "| v1 | MidBreakoutStrategyV1 | 1 | 1 | 1 | 0 |" in md


# 3: technische Kennzahlen erscheinen korrekt (in der Übersichtstabelle).
def test_technical_results_rendered():
    md = render_comparison_markdown(_comparison())
    # v0: 2/2/2/0, v1: 1/1/1/0 — als ganze Tabellenzeilen geprüft.
    assert "| v0 | MidBreakoutStrategy | 2 | 2 | 2 | 0 |" in md
    assert "| v1 | MidBreakoutStrategyV1 | 1 | 1 | 1 | 0 |" in md


# 4: Strategy-Metadaten und params erscheinen je Variante.
def test_strategy_params_rendered():
    md = render_comparison_markdown(_comparison())
    assert "### v0" in md
    assert "### v1" in md
    assert "| family | mid_breakout |" in md
    assert "| key | v0 |" in md
    assert "| name | MidBreakoutStrategy |" in md
    assert "| lookback_bars | 3 |" in md
    assert "| stop_distance_pct | 0.05 |" in md
    # v1-only Parameter erscheinen nur in der v1-Sektion.
    assert "| breakout_threshold_pct | 0.001 |" in md
    assert "| cooldown_bars | 3 |" in md


# 5: CostModel-Metadaten erscheinen je Variante.
def test_cost_model_rendered():
    md = render_comparison_markdown(_comparison())
    assert "Cost Model:" in md
    assert "| fee_rate | 0.0 |" in md  # v0
    assert "| fee_rate | 0.001 |" in md  # v1
    assert "| spread | 0.0 |" in md
    assert "| slippage | 0.0 |" in md


# 6: Pflicht-Notes erscheinen (Default, wenn nicht gesetzt).
def test_mandatory_notes_present_by_default():
    md = render_comparison_markdown(_comparison())  # ohne "notes"
    assert "## Notes" in md
    assert "- Synthetic data only." in md
    assert "- No profitability assessment." in md
    assert "- No trading recommendation." in md


# 7: Ausgabe ist deterministisch.
def test_output_is_deterministic():
    a = render_comparison_markdown(_comparison())
    b = render_comparison_markdown(_comparison())
    assert a == b


# 8: Fehlende optionale Felder werden stabil behandelt (keine Exception, Defaults).
def test_missing_optional_fields_are_stable():
    md = render_comparison_markdown({"variants": [{}]})
    assert "# Synthetic Strategy Comparison" in md  # Default-Titel
    assert "| name | unknown |" in md
    assert "| type | synthetic |" in md
    assert "| bars | 0 |" in md
    # Default-Label variant_0 und Null-Kennzahlen.
    assert "| variant_0 |  | 0 | 0 | 0 | 0 |" in md
    # Default-Notes trotz fehlendem notes-Feld.
    assert "- No profitability assessment." in md


# 8b: völlig leere Eingabe ist stabil (keine Variants, Defaults).
def test_empty_comparison_is_stable():
    md = render_comparison_markdown({})
    assert "## Dataset" in md
    assert "## Variants" in md
    assert "## Notes" in md


# 9: normalize_comparison liefert stabile Dict-Struktur.
def test_normalize_comparison_structure():
    norm = normalize_comparison({"variants": [{"label": "x"}]})
    assert set(norm.keys()) == {"title", "dataset", "variants", "notes"}
    assert set(norm["dataset"].keys()) == {"name", "type", "bars", "description"}
    variant = norm["variants"][0]
    assert set(variant.keys()) == {"label", "strategy", "cost_model", "technical_results"}
    assert variant["label"] == "x"
    assert variant["cost_model"] == {"fee_rate": 0.0, "spread": 0.0, "slippage": 0.0}
    assert variant["technical_results"] == {
        "signals_total": 0, "trades_total": 0, "approved_signals": 0, "rejected_signals": 0,
    }
    # Default-Label, wenn nicht gesetzt.
    assert normalize_comparison({"variants": [{}, {}]})["variants"][1]["label"] == "variant_1"


# 10: kein Ranking/Wertungs-Vokabular im gerenderten Report.
#     Hinweis: "profitability" steht legitim in der Disclaimer-Note
#     ("No profitability assessment.") und ist daher bewusst nicht in der Liste.
def test_no_evaluation_vocabulary_in_output():
    md = render_comparison_markdown(_comparison()).lower()
    for token in ("winner", "better", "worse", "ranking", "ending_equity"):
        assert token not in md, f"Vergleichsreport darf {token!r} nicht enthalten"


# 11: Statischer Scan -> Modul ohne Netzwerk-/Exchange-/Download-/Live-/Paper-Pfade.
def test_module_has_no_forbidden_paths():
    import inspect

    from liquent.backtesting import comparison_reporting as module

    source_code = inspect.getsource(module).lower()
    forbidden = [
        "li" + "ve",
        "pa" + "per",
        "exch" + "ange",
        "down" + "load",
        "soc" + "ket",
        "req" + "uests",
        "ht" + "tp://",
        "ht" + "tps://",
        "api_" + "key",
    ]
    for token in forbidden:
        assert token not in source_code, f"Modul darf {token!r} nicht enthalten"
