"""Strukturierter, synthetischer Vergleichsreport (LQ-013).

Spec: docs/lq-013-structured-synthetic-comparison-report.md

Isoliertes, additives Modul für **technische** Vergleichsreports mehrerer
synthetischer Backtest-/Signal-Varianten (z. B. v0 vs. v1). Es stellt Varianten
**nebeneinander** dar — rein deskriptiv:

- KEINE Bewertung, KEIN Ranking, KEIN "winner"/"besser"/"schlechter",
- KEINE Ergebnis-Interpretation, KEIN ``ending_equity``,
- KEINE Handelsempfehlung, KEINE Profitabilitätsaussage.

Alle Funktionen sind rein und deterministisch: keine I/O, kein Schreiben von
Dateien, keine Wall-Clock-Zeit, kein Zufall — nur Standardbibliothek. Der
Aufrufer erhält ausschließlich einen String bzw. ein normalisiertes Dict zurück.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

# Deterministische Feldreihenfolgen (Teil des stabilen Outputs).
_DATASET_FIELDS = ("name", "type", "bars", "description")
_STRATEGY_HEAD = ("family", "key", "name")
_COST_FIELDS = ("fee_rate", "spread", "slippage")
_RESULT_FIELDS = ("signals_total", "trades_total", "approved_signals", "rejected_signals")

_DEFAULT_TITLE = "Synthetic Strategy Comparison"
_DEFAULT_NOTES = (
    "Synthetic data only.",
    "No profitability assessment.",
    "No trading recommendation.",
)


def _format_value(value: object) -> str:
    """Deterministische, stabile Stringdarstellung eines skalaren Werts.

    Lokale Kopie (bewusst dupliziert, um nicht auf ein privates Symbol aus
    ``reporting.py`` zu koppeln). bool VOR int prüfen (bool ist int-Subklasse).
    """
    if isinstance(value, bool):
        return "True" if value else "False"
    return str(value)


def _normalize_dataset(dataset: Mapping[str, Any] | None) -> dict[str, Any]:
    data = dataset or {}
    return {
        "name": data.get("name", "unknown"),
        "type": data.get("type", "synthetic"),
        "bars": data.get("bars", 0),
        "description": data.get("description", ""),
    }


def _normalize_strategy(strategy: Mapping[str, Any] | None) -> dict[str, Any]:
    strat = strategy or {}
    params = strat.get("params", {})
    return {
        "family": strat.get("family", ""),
        "key": strat.get("key", ""),
        "name": strat.get("name", ""),
        "params": dict(params) if isinstance(params, Mapping) else {},
    }


def _normalize_cost_model(cost_model: Mapping[str, Any] | None) -> dict[str, Any]:
    cost = cost_model or {}
    return {field: cost.get(field, 0.0) for field in _COST_FIELDS}


def _normalize_results(results: Mapping[str, Any] | None) -> dict[str, Any]:
    res = results or {}
    return {field: res.get(field, 0) for field in _RESULT_FIELDS}


def _normalize_variant(variant: Mapping[str, Any] | None, index: int) -> dict[str, Any]:
    var = variant or {}
    return {
        "label": var.get("label", f"variant_{index}"),
        "strategy": _normalize_strategy(var.get("strategy")),
        "cost_model": _normalize_cost_model(var.get("cost_model")),
        "technical_results": _normalize_results(var.get("technical_results")),
    }


def normalize_comparison(comparison: Mapping[str, Any] | None) -> dict[str, Any]:
    """Stabilisiert eine Vergleichsstruktur zu einer deterministischen Form.

    Füllt fehlende optionale Felder mit robusten Defaults und erzwingt feste
    Feldreihenfolgen. ``params`` jeder Strategie bleibt in Einfügereihenfolge
    erhalten (die CLI setzt sie bereits sinnvoll). Reine Funktion, keine I/O.
    """
    comp = comparison or {}

    variants_in = comp.get("variants", [])
    if not isinstance(variants_in, Sequence) or isinstance(variants_in, (str, bytes)):
        variants_in = []
    variants = [_normalize_variant(v, i) for i, v in enumerate(variants_in)]

    notes_in = comp.get("notes")
    if isinstance(notes_in, Sequence) and not isinstance(notes_in, (str, bytes)):
        notes = [str(note) for note in notes_in]
    else:
        notes = list(_DEFAULT_NOTES)

    return {
        "title": comp.get("title", _DEFAULT_TITLE),
        "dataset": _normalize_dataset(comp.get("dataset")),
        "variants": variants,
        "notes": notes,
    }


def render_comparison_markdown(comparison: Mapping[str, Any] | None) -> str:
    """Erzeugt einen deterministischen, strukturierten Markdown-Vergleichsreport.

    Schreibt KEINE Datei — gibt nur den String zurück. Feste Abschnitts- und
    Spaltenreihenfolge; keine Bewertung, kein Ranking, keine Empfehlung.
    """
    comp = normalize_comparison(comparison)
    lines: list[str] = []

    lines.append(f"# {comp['title']}")
    lines.append("")

    # Dataset.
    dataset = comp["dataset"]
    lines.append("## Dataset")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    for field in _DATASET_FIELDS:
        lines.append(f"| {field} | {_format_value(dataset[field])} |")
    lines.append("")

    # Variants-Übersichtstabelle.
    lines.append("## Variants")
    lines.append("")
    lines.append("| Variant | Strategy | Signals | Trades | Approved | Rejected |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for variant in comp["variants"]:
        res = variant["technical_results"]
        lines.append(
            f"| {_format_value(variant['label'])} "
            f"| {_format_value(variant['strategy']['name'])} "
            f"| {_format_value(res['signals_total'])} "
            f"| {_format_value(res['trades_total'])} "
            f"| {_format_value(res['approved_signals'])} "
            f"| {_format_value(res['rejected_signals'])} |"
        )
    lines.append("")

    # Variant Parameters (Strategy + Cost Model je Variante).
    lines.append("## Variant Parameters")
    lines.append("")
    for variant in comp["variants"]:
        lines.append(f"### {variant['label']}")
        lines.append("")

        strategy = variant["strategy"]
        lines.append("Strategy:")
        lines.append("")
        lines.append("| Parameter | Value |")
        lines.append("|---|---|")
        for field in _STRATEGY_HEAD:
            lines.append(f"| {field} | {_format_value(strategy[field])} |")
        for key, value in strategy["params"].items():
            lines.append(f"| {key} | {_format_value(value)} |")
        lines.append("")

        cost = variant["cost_model"]
        lines.append("Cost Model:")
        lines.append("")
        lines.append("| Parameter | Value |")
        lines.append("|---|---|")
        for field in _COST_FIELDS:
            lines.append(f"| {field} | {_format_value(cost[field])} |")
        lines.append("")

    # Notes (deskriptive Hinweise; keine Empfehlung).
    lines.append("## Notes")
    lines.append("")
    for note in comp["notes"]:
        lines.append(f"- {note}")
    lines.append("")

    return "\n".join(lines)
