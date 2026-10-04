"""Pure customer-facing projections of the pilot contracts (no I/O)."""

from __future__ import annotations

from dataclasses import fields, replace
import html
import json
import math
from typing import Any

from liquent.backtesting.reporting import summary_to_dict, summary_to_markdown

from .contracts import MODEL_LIMITS, RESULT_SCHEMA, PilotResult


def _json_value(value: Any, path: str, notes: dict[str, str]) -> Any:
    """Copy JSON values, replacing non-finite numbers at every nesting level."""
    if isinstance(value, float) and not math.isfinite(value):
        notes[path] = (
            "Nicht definiert oder nicht endlich; als JSON null dargestellt."
            + (" Profit Factor: bei Gewinnen ohne Verluste ist der Quotient unendlich."
               if path.endswith(".profit_factor") and value == math.inf else "")
        )
        return None
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("Report dictionaries require string keys")
        return {key: _json_value(item, f"{path}.{key}", notes)
                for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item, f"{path}[{index}]", notes)
                for index, item in enumerate(value)]
    raise TypeError(f"Unsupported report value at {path}: {type(value).__name__}")


def pilot_to_dict(result: PilotResult) -> dict:
    """Return result-v1 without ranking, mutation or fabricated results.

    Backend no-trade defaults remain intact. Non-finite values become null;
    their paths and explanations are added to evidence.metric_notes.
    """
    variants = []
    for variant in result.variants:
        notes: dict[str, str] = {}
        item = _json_value({
            "variant_id": variant.variant_id,
            "input_fingerprint": variant.input_fingerprint,
            "status": variant.status,
            "inputs": variant.inputs,
            "summary": (summary_to_dict(variant.summary)
                        if variant.summary is not None else None),
            "evidence": variant.evidence,
            "error": variant.error,
        }, "variant", notes)
        if notes:
            evidence = item["evidence"] if item["evidence"] is not None else {}
            metric_notes = dict(evidence.get("metric_notes") or {})
            for path, explanation in notes.items():
                previous = metric_notes.get(path)
                metric_notes[path] = (
                    f"{previous}; {explanation}" if previous is not None else explanation
                )
            evidence["metric_notes"] = metric_notes
            item["evidence"] = evidence
        variants.append(item)
    # Envelope values obey the same strict JSON rule as nested parameters.
    envelope_notes: dict[str, str] = {}
    payload = _json_value({
        "schema": RESULT_SCHEMA,
        "pilot_id": result.pilot_id,
        "order": result.order,
        "data_quality": result.data_quality,
        "variants": variants,
        "runtime": result.runtime,
        "configuration": result.configuration,
        "model_limits": list(MODEL_LIMITS),
    }, "result", envelope_notes)
    if envelope_notes:
        warnings = list(payload["data_quality"].get("warnings") or [])
        warnings.extend(f"Berichtsserialisierung: {path}: {note}"
                        for path, note in envelope_notes.items())
        payload["data_quality"]["warnings"] = warnings
    return payload


def _escape(value: str) -> str:
    # Entities cannot introduce Markdown structure, links, code or raw HTML.
    text = " ".join(value.splitlines())
    special = "\\|`*_{}[]()#+!"
    return "".join(f"&#{ord(char)};" if char in special else html.escape(char, quote=True)
                   for char in text)


def _safe(value: Any) -> Any:
    """Sanitize all metadata before passing it to the unescaped legacy renderer."""
    if isinstance(value, str):
        return _escape(value)
    if isinstance(value, float) and not math.isfinite(value):
        return "Nicht definiert / nicht endlich (JSON: null)"
    if isinstance(value, dict):
        return {_escape(str(key)): _safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    return value


def _cell(value: Any) -> str:
    if value is None:
        return "Nicht vorhanden"
    if isinstance(value, (dict, list, tuple)):
        return _escape(json.dumps(value, ensure_ascii=False, allow_nan=False))
    return _escape(str(value))


def _table(title: str, data: dict) -> list[str]:
    return [f"### {title}", "", "| Feld | Wert |", "|---|---|", *[
        f"| {_cell(key)} | {_cell(value)} |" for key, value in data.items()
    ], ""]


_STATUS = {
    "succeeded": "Ausgeführt (succeeded); keine Qualitäts- oder Gewinnzusage",
    "no_signals": "Keine Signale (no_signals); nicht mit abgelehnten Signalen gleichzusetzen",
    "failed": "Fehlgeschlagen (failed); nicht bestanden",
    "blocked_data": "Nicht ausgeführt (blocked_data): Datenprüfung blockiert; nicht bestanden",
}


def pilot_to_markdown(result: PilotResult) -> str:
    """Render a German envelope, retaining supplied variant order and evidence."""
    payload = pilot_to_dict(result)
    lines = ["# Liquent Research-Pilot – Kundenbericht", "",
             f"Pilot-ID: {_cell(payload['pilot_id'])}", "",
             "Dieser Bericht dokumentiert eine Simulation mit den vorab festgelegten "
             "Eingaben. Er enthält keine persönliche Beratung oder individuelle "
             "Handels- oder Strategieempfehlung.", "",
             "## So lesen Sie den Bericht", "",
             "1. Datenqualität und Modellgrenzen prüfen. Bei blockierten Daten "
             "liegt keine ausgeführte Simulation vor.",
             "2. Die tatsächlich verwendeten Eingaben und Kostenannahmen mit "
             "dem Auftrag vergleichen.",
             "3. Ergebnisse je Variante lesen. Unterschiedliche Positionsgrößen "
             "und Risikoeinheiten erlauben keine direkte Rangfolge.",
             "4. Technische Fehler schriftlich mit Pilot-ID und betroffener "
             "Berichtsstelle melden; neue Daten oder Einstellungen sind ein neuer Umfang.", "",
             "Brutto-PnL bezeichnet das simulierte Ergebnis vor Kosten; Netto-PnL "
             "das Ergebnis nach den ausgewiesenen Kosten. Max. Drawdown bezeichnet "
             "den größten simulierten Rückgang vom bisherigen Höchststand. "
             "Diese Werte sind keine Prognose künftiger Ergebnisse.", "",
             "## Modellgrenzen – vor jeder Interpretation beachten", ""]
    lines.extend(f"- {limit}" for limit in MODEL_LIMITS)
    lines.extend(["", "## Auftrag und Annahmen", ""])
    lines.extend(_table("Auftrag (einschließlich Datenherkunft und Annahmen)", payload["order"]))
    lines.extend(["## Datenqualität", "",
                  "Der Datenstatus beschreibt die Datenprüfung, nicht den Erfolg eines Backtests.", ""])
    lines.extend(_table("Prüfung, Zeitraum, Lücken und Historie", payload["data_quality"]))
    lines.extend(["## Variantenvergleich", "",
                  "Reihenfolge wie beauftragt; kein Ranking und keine Auswahl einer besten Variante.", "",
                  "| Variante | Status | Trades | Freigegebene Signale | Abgelehnte Signale |",
                  "|---|---|---|---|---|"])
    for item in payload["variants"]:
        summary = item["summary"]
        counts = ([summary[key] for key in (
            "number_of_trades", "approved_signals", "rejected_signals"
        )] if summary is not None else [None, None, None])
        status = _STATUS.get(item["status"], f"Unbekannter Status: {item['status']}")
        lines.append("| " + " | ".join(_cell(v) for v in [
            item["variant_id"], status, *counts
        ]) + " |")
    lines.extend(["", "Kennzahlen in der vereinbarten Preiseinheit; keine Rangfolge. "
                  "Ohne Trades sind Leistungskennzahlen nicht aussagekräftig.", "",
                  "| Variante | Brutto-PnL | Gebühren | Spread | Slippage | Netto-PnL | Max. Drawdown |",
                  "|---|---|---|---|---|---|---|"])
    for item in payload["variants"]:
        totals = (item["evidence"] or {}).get("cost_totals", {})
        summary = item["summary"]
        values = [totals.get(key) for key in ("gross_pnl", "fee", "spread", "slippage", "net_pnl")]
        drawdown = summary["metrics"].get("max_drawdown") if summary and summary["number_of_trades"] else None
        lines.append("| " + " | ".join(_cell(value) for value in [item["variant_id"], *values, drawdown]) + " |")
    if not payload["variants"]:
        lines.extend(["", "Keine Varianten-Ergebnisse vorhanden; "
                      "kein Lauf als ausgeführt oder bestanden ausgewiesen."])
    lines.extend(["", "## Varianten – Metriken und Evidenz", "",
                  "Kosten und PnL/Equity: Preis-/Abrechnungseinheit des Auftrags. "
                  "fee_rate und slippage sind Anteile des Notional "
                  "(0.001 = 0.1 %); spread ist ein absoluter Preisaufschlag pro Einheit. "
                  "Kosten werden für Einstieg und Ausstieg angesetzt. "
                  "Win Rate ist ein Anteil, Profit Factor dimensionslos, "
                  "Drawdown absolut; R-Multiple siehe Modellgrenzen.", ""])
    for variant, item in zip(result.variants, payload["variants"]):
        lines.extend([f"### Variante: {_cell(item['variant_id'])}", "",
                      f"Status: {_cell(_STATUS.get(item['status'], item['status']))}", "",
                      f"Input-Fingerprint: {_cell(item['input_fingerprint'])}", ""])
        if item["error"] is not None:
            lines.extend([f"Fehler: {_cell(item['error'])}", ""])
        lines.extend(_table("Vollständige deklarierte Eingaben", item["inputs"]))
        if variant.summary is None:
            lines.extend(["Keine Ergebniszusammenfassung vorhanden; keine Nullergebnisse erfunden.", ""])
        else:
            safe_summary = replace(variant.summary, **{
                field.name: _safe(getattr(variant.summary, field.name))
                for field in fields(variant.summary)
            })
            # Legacy reporting looks these structural keys up by exact name.
            # Escaping fee_rate to fee&#95;rate would silently display its 0 default.
            safe_summary = replace(safe_summary,
                cost_metadata=({key: _safe(variant.summary.cost_metadata[key])
                                for key in ("fee_rate", "spread", "slippage")
                                if key in variant.summary.cost_metadata}
                               if variant.summary.cost_metadata is not None else None),
                safety_flags={key: variant.summary.safety_flags.get(key, False)
                              for key in ("live_execution", "network_calls", "paper_trading")})
            if variant.summary.number_of_trades == 0:
                safe_summary = replace(safe_summary, metrics={
                    key: "Nicht aussagekräftig: keine Trades" for key in safe_summary.metrics
                })
                lines.extend(["Nicht aussagekräftig: keine Trades. "
                              "Die tatsächlichen Backend-Metrikwerte bleiben im JSON erhalten.", ""])
            if item["status"] in ("failed", "blocked_data"):
                lines.extend(["Vorhandene Teilergebnisse: kein vollständig erfolgreicher Lauf.", ""])
            # Nest legacy headings under this variant without altering legacy reporting.
            legacy = summary_to_markdown(safe_summary)
            lines.extend(("###" + line if line.startswith("#") else line)
                         for line in legacy.splitlines())
            lines.append("")
        evidence = item["evidence"]
        if evidence is None:
            lines.extend(["Keine zusätzliche Evidenz vorhanden.", ""])
        else:
            for key, title in (
                ("effective_risk", "Wirksames Risiko (Parameter und tatsächliche Wirkung)"),
                ("runner_parameters", "Tatsächliche Runner-Parameter"),
                ("cost_totals", "Kosten und Brutto-/Netto-PnL in Auftragseinheit"),
                ("metric_notes", "Metrik-Erklärungen (null: nicht definiert / nicht endlich)"),
            ):
                lines.extend(_table(title, evidence.get(key) or {}))
            lines.extend(["Vollständige Einzel-Trades und Equity-Kurve stehen unter dieser "
                          "Varianten-ID und diesem Input-Fingerprint in `evidence.json`. "
                          "Die Original-CSV ist nicht Teil der Ausgabe.", ""])
    lines.extend(["## Wiederholung und Reproduzierbarkeit", "",
                  "Für eine Wiederholung dieselben Daten (Dataset-Fingerprint), "
                  "vollständigen Varianten-Eingaben und die vereinbarte Konfiguration "
                  "mit derselben Implementierung und Python-Laufzeit verwenden. "
                  "Pilot-, Input- und Implementierungs-Fingerprints dienen der Zuordnung. "
                  "Keine neuen Läufe oder Datenzugriffe werden durch diesen Bericht ausgelöst.", ""])
    lines.extend(_table("Laufzeit und Implementierungsumfang", payload["runtime"]))
    lines.extend(["Vollständige vereinbarte Konfiguration: `agreed-config.json`; "
                  "ebenfalls unverändert in `evidence.json` enthalten.", ""])
    return "\n".join(lines)
