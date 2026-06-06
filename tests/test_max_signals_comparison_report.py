"""Synthetischer Vergleichsreport für max_signals_per_day (LQ-016 Phase 2).

Macht die technische Wirkung des UTC-Tageslimits über den bestehenden
strukturierten Comparison-Report sichtbar — rein deterministisch, KEINE
Echtdaten, KEINE Datei, KEIN Runner nötig (nur ``generate_signals``). Es werden
ausschließlich Signalzahlen gezählt; keine Bewertung, kein Ranking, keine
Profitabilitätsaussage.
"""

from liquent.backtesting.comparison_reporting import (
    normalize_comparison,
    render_comparison_markdown,
)
from liquent.strategy import MidBreakoutStrategyV1

from helpers.synthetic_data import build_stair_breakout_for_cooldown

_TITLE = "Synthetic max_signals_per_day comparison"
_NOTES = [
    "Synthetic data only.",
    "No profitability assessment.",
    "No trading recommendation.",
    "Daily signal limit is a technical signal-density guard.",
]


def _strategy(max_signals_per_day):
    return MidBreakoutStrategyV1(
        lookback_bars=12,
        stop_distance_pct=0.01,
        breakout_threshold_pct=0.0,
        cooldown_bars=0,
        allow_short=True,
        min_strength=0.0,
        max_signals_per_day=max_signals_per_day,
    )


def _signal_count(dataset, max_signals_per_day) -> int:
    return len(_strategy(max_signals_per_day).generate_signals(dataset.market_data))


def _variant(label, max_signals_per_day, signals_total) -> dict:
    return {
        "label": label,
        "strategy": {
            "family": "mid_breakout",
            "key": "v1",
            "name": "MidBreakoutStrategyV1",
            "params": {
                "lookback_bars": 12,
                "stop_distance_pct": 0.01,
                "breakout_threshold_pct": 0.0,
                "cooldown_bars": 0,
                "allow_short": True,
                "min_strength": 0.0,
                "max_signals_per_day": max_signals_per_day,
            },
        },
        "cost_model": {"fee_rate": 0.0, "spread": 0.0, "slippage": 0.0},
        # Reine Signaldichte-Betrachtung: nur signals_total ist relevant; die
        # übrigen technischen Felder bleiben 0 (kein Runner-Lauf nötig).
        "technical_results": {
            "signals_total": signals_total,
            "trades_total": 0,
            "approved_signals": 0,
            "rejected_signals": 0,
        },
    }


def _build_comparison() -> dict:
    dataset = build_stair_breakout_for_cooldown()
    n_none = _signal_count(dataset, None)
    n_one = _signal_count(dataset, 1)
    n_two = _signal_count(dataset, 2)
    return {
        "title": _TITLE,
        "dataset": {
            "name": dataset.name,
            "type": "synthetic",
            "bars": len(dataset.market_data),
            "description": dataset.description,
        },
        "variants": [
            _variant("v1_no_daily_limit", None, n_none),
            _variant("v1_daily_limit_1", 1, n_one),
            _variant("v1_daily_limit_2", 2, n_two),
        ],
        "notes": list(_NOTES),
    }


# 0: verifizierte Signalzahlen auf dem stair-Dataset (Basis aller Aussagen).
def test_signal_counts_are_as_verified():
    dataset = build_stair_breakout_for_cooldown()
    assert _signal_count(dataset, None) == 5
    assert _signal_count(dataset, 1) == 1
    assert _signal_count(dataset, 2) == 2


# 1: Report enthält den Titel.
def test_report_contains_title():
    md = render_comparison_markdown(_build_comparison())
    assert f"# {_TITLE}" in md


# 2: Report enthält den Dataset-Abschnitt.
def test_report_contains_dataset():
    md = render_comparison_markdown(_build_comparison())
    assert "## Dataset" in md
    assert "| name | stair_breakout_for_cooldown |" in md
    assert "| type | synthetic |" in md
    assert "| bars | 18 |" in md


# 3: Report enthält die drei Varianten.
def test_report_contains_variants():
    md = render_comparison_markdown(_build_comparison())
    for label in ("v1_no_daily_limit", "v1_daily_limit_1", "v1_daily_limit_2"):
        assert f"### {label}" in md


# 4: Varianten-Tabelle zeigt die technischen Signalzahlen 5 / 1 / 2.
def test_report_contains_signal_counts():
    md = render_comparison_markdown(_build_comparison())
    assert "| v1_no_daily_limit | MidBreakoutStrategyV1 | 5 |" in md
    assert "| v1_daily_limit_1 | MidBreakoutStrategyV1 | 1 |" in md
    assert "| v1_daily_limit_2 | MidBreakoutStrategyV1 | 2 |" in md


# 5: Report weist die max_signals_per_day-Parameter None / 1 / 2 aus.
def test_report_contains_max_signals_params():
    md = render_comparison_markdown(_build_comparison())
    assert "| max_signals_per_day | None |" in md
    assert "| max_signals_per_day | 1 |" in md
    assert "| max_signals_per_day | 2 |" in md


# 6: technische Relationen (nur Zählwerte, keine Interpretation).
def test_technical_relations_hold():
    dataset = build_stair_breakout_for_cooldown()
    no_limit = _signal_count(dataset, None)
    limit_1 = _signal_count(dataset, 1)
    limit_2 = _signal_count(dataset, 2)
    assert no_limit > limit_1
    assert limit_1 == 1
    assert limit_2 == 2
    assert limit_2 >= limit_1


# 7: Pflicht-Notes inkl. der Zusatz-Note erscheinen.
def test_report_contains_mandatory_notes():
    md = render_comparison_markdown(_build_comparison())
    for note in _NOTES:
        assert f"- {note}" in md


# 8: keine Bewertungs-/Profitabilitätsbegriffe (Disclaimer NICHT blockieren).
def test_report_has_no_evaluation_terms():
    md = render_comparison_markdown(_build_comparison()).lower()
    # "recommendation" steht legitim im Disclaimer ("No trading recommendation.")
    # und ist daher bewusst NICHT in der Liste — geprüft wird "recommended".
    forbidden = [
        "ending_equity", "winner", "better", "worse",
        "recommended", "profitable", "performance",
    ]
    for token in forbidden:
        assert token not in md, f"Report darf {token!r} nicht enthalten"


# 9: Determinismus -> gleicher Input liefert byte-identisches Markdown.
def test_report_is_deterministic():
    a = render_comparison_markdown(_build_comparison())
    b = render_comparison_markdown(_build_comparison())
    assert a == b


# 10: normalize_comparison liefert stabile Struktur (kein I/O, reine Funktion).
def test_normalize_comparison_structure():
    norm = normalize_comparison(_build_comparison())
    assert norm["title"] == _TITLE
    assert len(norm["variants"]) == 3
    assert norm["variants"][0]["strategy"]["params"]["max_signals_per_day"] is None
    assert norm["variants"][1]["strategy"]["params"]["max_signals_per_day"] == 1


# 11: Statischer Scan -> diese Testdatei ohne verbotene Netzwerk-/Ausführungs-Pfade.
#     Verbotsliste fragmentbasiert, damit sie sich nicht selbst trifft.
def test_module_has_no_forbidden_paths():
    import inspect
    import sys

    module = sys.modules[__name__]
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
        assert token not in source_code, f"Testdatei darf {token!r} nicht enthalten"
