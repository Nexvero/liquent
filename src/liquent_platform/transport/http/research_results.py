"""Read-only, escaped HTML projection of stored backtest summaries."""

from html import escape
import math
from urllib.parse import quote
from liquent_platform.transport.http.ui_brand import STYLE, brand_document


STATUS_LABELS = {
    "ready": "Bereit zur Ausführung",
    "queued": "Wartet auf Ausführung",
    "running": "Wird ausgeführt",
    "succeeded": "Erfolgreich abgeschlossen",
    "failed": "Ausführung fehlgeschlagen",
    "cancelled": "Abgebrochen",
    "invalidated": "Ungültig geworden",
}


def page(title: str, content: str) -> str:
    return brand_document(
        '<!doctype html><html lang="de"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{escape(title)} · Liquent</title><style>{STYLE}</style>'
        f'</head><body><main>{content}</main></body></html>'
    )


def _number(value: object, *, percent: bool = False, detailed: bool = False) -> str:
    if type(value) not in (int, float):
        return "Nicht verfügbar"
    try:
        scaled = value * 100 if percent else value
        if not math.isfinite(scaled):
            return "Nicht verfügbar"
        if detailed and scaled != 0 and abs(scaled) < 0.000001:
            # Even the smallest nonzero stored float must not look like zero.
            rendered = f"{scaled:.6e}"
        elif detailed:
            rendered = f"{scaled:,.6f}"
            whole, fraction = rendered.rsplit(".", 1)
            rendered = whole + "." + fraction.rstrip("0").ljust(2, "0")
        else:
            rendered = f"{scaled:,.2f}"
    except (OverflowError, ValueError):
        return "Nicht verfügbar"
    rendered = rendered.replace(",", "_").replace(".", ",").replace("_", ".")
    return rendered + (" %" if percent else "")


_PARAMETERS = {
    "seed", "starting_equity", "sizing_mode", "risk_per_trade",
    "risk_per_trade_pct", "max_position_size", "max_total_exposure",
    "max_position_notional", "max_daily_drawdown", "max_daily_loss",
    "max_losing_streak", "bars", "period_start", "period_end", "data_timeframe",
    "data_symbol", "strategy", "signals_total", "trade_simulation",
}
_STRATEGY = {"lookback", "lookback_bars", "stop_distance_pct", "min_strength", "allow_short",
             "breakout_threshold_pct", "cooldown_bars", "max_signals_per_day"}
_COSTS = {"fee_rate", "spread", "slippage"}


def _mapping(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _scalar(value: object) -> str:
    if isinstance(value, str):
        return escape(value)
    if type(value) is bool:
        return "Ja" if value else "Nein"
    # Parameters must retain small cost rates rather than rounding them to zero.
    if type(value) in (int, float):
        try:
            if math.isfinite(value):
                return escape(str(value))
        except OverflowError:
            pass
    return "Nicht verfügbar"


def _fields(title: str, values: object, allowed: set[str]) -> str:
    data = _mapping(values)
    rows = ''.join(f'<tr><th scope="row">{escape(key)}</th><td>{_scalar(data[key])}</td></tr>'
                   for key in sorted(allowed) if key in data)
    return (f'<section><h3>{escape(title)}</h3><table><tbody>{rows}</tbody></table></section>'
            if rows else f'<section><h3>{escape(title)}</h3><p>Nicht verfügbar</p></section>')


def _limits() -> str:
    return ('<section class="notice"><h2>Verbindliche Modellgrenzen</h2>'
            '<p>Ein Trade wird nach einem Datenbalken geschlossen (Close-to-Close). '
            'stop_price dient nur der Positionsgrößenberechnung: keine tatsächliche '
            'Stop-Loss-Ausführung und kein Stop-Ausstieg. OHLCV-Breakouts verwenden '
            'den Schlusskurs als Mittelkurs-Proxy.</p><p>Das R-Multiple ist net_pnl / quantity, '
            'kein stopbasiertes Rendite-Risiko-Verhältnis. Drawdown wird kumulativ ohne '
            'Tagesreset geprüft; day_realized_loss bleibt 0, max_daily_loss ist kein '
            'wirksamer Verlustschutz. Keine überlappenden Positionen, Parametersuche, '
            'persönliche Beratung oder individuelle Handelsempfehlungen.</p></section>')


def _details(summary: dict, actual: dict | None = None) -> str:
    parameters = _mapping(summary.get("parameters"))
    costs = _mapping(summary.get("cost_metadata", summary.get("cost_model")))
    content = _fields("Tatsächlich gespeicherte Laufparameter", parameters, _PARAMETERS)
    strategy = _mapping(summary.get("strategy_metadata", summary.get("strategy")))
    content += _fields("Strategieparameter", strategy.get("params", strategy), _STRATEGY)
    # Stored metadata has precedence, including missing/invalid values. No defaults.
    content += _fields("Kostenannahmen", {key: costs[key] if key in costs else parameters[key]
                       for key in _COSTS if key in costs or key in parameters}, _COSTS)
    content += ('<p>fee_rate und slippage sind Anteile des Handelswerts; spread ist ein '
                'absoluter Preisaufschlag pro Einheit. Kosten fallen bei Ein- und Ausstieg an.</p>')
    totals = _mapping(_mapping(actual).get("cost_totals"))
    content += '<section><h3>Tatsächliches simuliertes Ergebnis und Kosten</h3><dl class="cards">'
    for key, label in (("gross_pnl", "Bruttoergebnis"), ("fee", "Gebühren"),
                       ("spread", "Spread-Kosten"), ("slippage", "Slippage-Kosten"),
                       ("total", "Gesamtkosten"), ("net_pnl", "Nettoergebnis")):
        content += f'<div><dt>{label}</dt><dd>{_number(totals.get(key), detailed=True)}</dd></div>'
    content += ('</dl><p>Nur gespeicherte Werte; keine Rekonstruktion aus Kapitalständen. '
                'Anzeige mit bis zu sechs Nachkommastellen; kleinere von null verschiedene '
                'Beträge in wissenschaftlicher Schreibweise. Ungerundete gespeicherte Werte '
                'stehen im JSON-Download. Gerundete Einzelbeträge können von der '
                'angezeigten Summe abweichen.</p></section>')
    effective = _mapping(_mapping(actual).get("effective_risk"))
    content += _fields("Gespeicherte Risikowirkung", effective, _PARAMETERS)
    content += '<p>Deklarierte Risikolimits sind nicht automatisch wirksame Schutzmechanismen; siehe Modellgrenzen. Im absoluten Modus werden Prozent-Risiko, Notional-Limit und Verlustserie nicht verwendet.</p>'
    return content


def _pilot_sections(pilot: dict) -> str:
    content = '<h2>Drei vereinbarte Varianten</h2><p>Reihenfolge wie vereinbart; kein Ranking und keine Strategieempfehlung.</p>'
    variants = pilot.get("variants")
    if not isinstance(variants, list) or len(variants) != 3 or not all(isinstance(v, dict) for v in variants):
        return content + '<p>Varianten-Evidenz unvollständig oder ungültig; kein vollständiger Vergleich verfügbar.</p>'
    labels = {"succeeded": "Ausgeführt", "no_signals": "Keine Signale",
              "failed": "Fehlgeschlagen", "blocked_data": "Nicht ausgeführt: Datenprüfung blockiert"}
    for variant in variants:
        identifier = variant.get("variant_id")
        state = variant.get("status")
        label = labels.get(state, "Status nicht verfügbar") if isinstance(state, str) else "Status nicht verfügbar"
        content += f'<section><h2>Variante: {_scalar(identifier)}</h2><p><strong>{label}</strong></p>'
        content += _fields("Eingabebindung", variant, {"input_fingerprint"})
        inputs = _mapping(variant.get("inputs"))
        content += _fields("Vereinbarte Eingaben", inputs, {"strategy", "seed", "hypothesis", "dataset_fingerprint", "timeframe"})
        for key, title, allowed in (("strategy_parameters", "Vereinbarte Strategieparameter", _STRATEGY),
                                    ("risk", "Vereinbartes Risiko", _PARAMETERS | {"initial_equity"}),
                                    ("costs", "Vereinbarte Kosten", _COSTS)):
            content += _fields(title, inputs.get(key), allowed)
        summary = _mapping(variant.get("summary"))
        if summary:
            content += _summary_sections(summary) + _details(summary, _mapping(variant.get("evidence")))
        else:
            content += '<p>Keine Ergebniszusammenfassung vorhanden; keine Nullergebnisse unterstellt.</p>'
        if isinstance(variant.get("error"), str):
            content += f'<p>Fehler: {escape(variant["error"])}</p>'
        content += '</section>'
    return content


def result_document(job_id: str, status: str, evidence: dict | None) -> str:
    content = (
        '<nav><a href="/research">← Alle Research-Aufträge</a></nav>'
        '<h1>Research-Ergebnis</h1>'
        f'<p><strong>{escape(STATUS_LABELS.get(status, "Status nicht verfügbar"))}</strong></p>'
        f'<p><small>Auftrag: <code>{escape(job_id)}</code></small></p>'
        '<p class="notice">Backtest / Simulation — keine Live-Trades und keine '
        'Handelsempfehlung. Ein erfolgreicher Lauf bestätigt die Ausführung, '
        'nicht die Profitabilität einer Strategie.</p>'
    )
    content += _limits()
    if not isinstance(evidence, dict):
        message = (
            "Für diesen abgeschlossenen Auftrag ist keine Auswertung verfügbar."
            if status == "succeeded"
            else "Eine Auswertung liegt noch nicht vor."
            if status in ("queued", "running")
            else "Für diesen Auftrag liegt keine erfolgreiche Auswertung vor."
        )
        return page("Research-Ergebnis", content + f"<section><h2>Auswertung</h2><p>{message}</p></section>")

    content += f'<p><a href="/v1/research/jobs/{quote(job_id, safe="")}/evidence" download="research-evidence.json">Ergebnis-Evidenz als JSON herunterladen</a></p>'
    if "pilot_result" in evidence:
        pilot = _mapping(evidence.get("pilot_result"))
        if pilot.get("schema") != "liquent.research-pilot.result.v1":
            content += '<p>Pilot-Ergebnisformat nicht verfügbar oder nicht unterstützt.</p>'
        else:
            content += _pilot_sections(pilot)
    else:
        content += _summary_sections(evidence) + _details(evidence)
    return page("Research-Ergebnis", content)


def _summary_sections(evidence: dict) -> str:

    # Whitelist public summary fields. Never render arbitrary evidence or metadata.
    title = evidence.get("title")
    strategy = evidence.get("strategy_name")
    content = '<section><h2>Experiment</h2>'
    if isinstance(title, str):
        content += f'<p>{escape(title)}</p>'
    if isinstance(strategy, str):
        content += f'<p>Strategie: {escape(strategy)}</p>'
    content += '</section><h2>Ergebnisübersicht</h2><p>Kapitalwerte in Simulationseinheiten; keine Währung unterstellt.</p><dl class="cards">'
    for label, key in (
        ("Startkapital", "starting_equity"),
        ("Endkapital", "ending_equity"),
        ("Simulierte Trades", "number_of_trades"),
        ("Freigegebene Signale", "approved_signals"),
        ("Abgelehnte Signale", "rejected_signals"),
    ):
        value = evidence.get(key)
        rendered = str(value) if key.endswith(("trades", "signals")) and type(value) is int and value >= 0 else _number(value)
        content += f'<div><dt>{label}</dt><dd>{rendered}</dd></div>'
    content += '</dl><section><h2>Kennzahlen</h2><table><thead><tr><th scope="col">Kennzahl</th><th scope="col">Wert</th></tr></thead><tbody>'
    metrics = evidence.get("metrics")
    metrics = metrics if isinstance(metrics, dict) else {}
    if evidence.get("number_of_trades") == 0:
        content += '<tr><td colspan="2">Ohne Trades sind Leistungskennzahlen nicht aussagekräftig; gespeicherte Werte sind keine Erfolgsbelege.</td></tr>'
    for key, label, percent in (
        ("win_rate", "Anteil gewinnender Trades", True),
        ("profit_factor", "Profitfaktor (Gewinn / Verlust)", False),
        ("max_drawdown", "Größter Kapitalrückgang (absolut)", False),
        ("average_r_multiple", "Durchschnittliches R-Multiple", False),
        ("expectancy", "Durchschnittliches Ergebnis pro Trade", False),
    ):
        content += f'<tr><th scope="row">{label}</th><td>{_number(metrics.get(key), percent=percent)}</td></tr>'
    content += '</tbody></table><p><small>Fehlende oder nicht endliche Werte werden nicht als null oder als Erfolg interpretiert.</small></p></section>'
    notes = evidence.get("risk_notes")
    notes = notes if isinstance(notes, (list, tuple)) else ()
    content += '<section><h2>Risikohinweise aus dem Lauf</h2>'
    content += '<ul>' + ''.join(f'<li>{escape(note)}</li>' for note in notes if isinstance(note, str)) + '</ul>' if notes else '<p>Keine Hinweise gespeichert.</p>'
    content += '</section>'
    return content
