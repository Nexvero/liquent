"""Read-only, escaped HTML projection of stored backtest summaries."""

from html import escape
import math


STYLE = """:root{font-family:system-ui,sans-serif;color:#172b3a;background:#f3f6f8}
body{margin:0}main{max-width:960px;margin:auto;padding:32px 20px}
a{color:#075e78;text-underline-offset:3px}h1{font-size:2rem}
.notice{border-left:4px solid #18798a;padding:16px;background:#e4f1f3}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
.cards div,section{background:white;border:1px solid #d6e0e6;border-radius:10px;padding:18px}
section{margin:20px 0}dt{font-weight:600}dd{margin:8px 0 0;font-size:1.15rem}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:12px 8px;border-bottom:1px solid #e4ebef;overflow-wrap:anywhere}
code{overflow-wrap:anywhere}li{padding:8px 0}small{color:#475a69}
@media(max-width:480px){main{padding:20px 12px}th,td{padding:10px 4px}}
"""

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
    return (
        '<!doctype html><html lang="de"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{escape(title)} · Liquent</title><style>{STYLE}</style>'
        f'</head><body><main>{content}</main></body></html>'
    )


def _number(value: object, *, percent: bool = False) -> str:
    if type(value) not in (int, float) or not math.isfinite(value):
        return "Nicht verfügbar"
    rendered = f"{value * 100 if percent else value:,.2f}"
    rendered = rendered.replace(",", "_").replace(".", ",").replace("_", ".")
    return rendered + (" %" if percent else "")


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
    if evidence is None:
        message = (
            "Für diesen abgeschlossenen Auftrag ist keine Auswertung verfügbar."
            if status == "succeeded"
            else "Eine Auswertung liegt noch nicht vor."
            if status in ("queued", "running")
            else "Für diesen Auftrag liegt keine erfolgreiche Auswertung vor."
        )
        return page("Research-Ergebnis", content + f"<section><h2>Auswertung</h2><p>{message}</p></section>")

    # Whitelist public summary fields. Never render arbitrary evidence or metadata.
    title = evidence.get("title")
    strategy = evidence.get("strategy_name")
    content += '<section><h2>Experiment</h2>'
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
    return page("Research-Ergebnis", content)
