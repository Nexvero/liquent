"""Experiment-Reporting/-Export — Serialisierungsbasis (LQ-005 Phase 5).

Spec: liquent/06_Backtesting/Backtesting_Framework_Spec.md
ADR: liquent/10_Decisions/ADR-003_Backtesting_Before_Automation.md

Überführt ein ``BacktestResult`` in eine stabile, auditierbare, serialisierbare
Experiment-Zusammenfassung. Dies ist NUR die interne Basis — es werden in
dieser Phase bewusst KEINE Obsidian-/Vault-Dateien geschrieben (Phase 6).

Alle Funktionen sind rein und deterministisch (keine Seiteneffekte, kein I/O,
keine Wall-Clock-Zeit, keine Zufalls-IDs) und nutzen ausschließlich die
Standardbibliothek. Die Zusammenfassung trifft KEINE Profitabilitätsaussage und
spricht KEINE Handelsempfehlung aus — sie ist rein deskriptiv.
"""

from __future__ import annotations

from dataclasses import dataclass

from .runner import BacktestResult

# Sicherheits-/Modus-Flags, die aus den Lauf-Parametern übernommen werden.
# Reihenfolge ist Teil des stabilen Markdown-/Dict-Outputs.
_SAFETY_FLAG_NAMES = ("live_execution", "network_calls", "paper_trading")


@dataclass(frozen=True)
class BacktestExperimentSummary:
    """Immutable, serialisierbare Zusammenfassung eines Backtest-Laufs.

    Leichte Audit-Struktur ohne mutable Defaults — alle Felder sind Pflicht und
    werden von ``summarize_backtest_result`` explizit befüllt. Enthält nur
    deskriptive Werte (Gate-Zählungen, Metriken, reproduzierbare Parameter,
    Risiko-Hinweise, Sicherheits-Flags); keine Bewertung, keine Empfehlung.

    Felder:
        experiment_id:    Deterministische ID des Laufs (aus dem Result).
        title:            Anzeigetitel des Experiments.
        strategy_name:    Name der genutzten Strategie (aus den Parametern).
        starting_equity:  Start-Equity.
        ending_equity:    End-Equity.
        number_of_trades: Anzahl abgeschlossener (simulierter) Trades.
        approved_signals: Von der Risk Engine freigegebene Signale.
        rejected_signals: Von der Risk Engine abgelehnte Signale.
        metrics:          Standardmetriken (Kopie aus dem Result).
        parameters:       Reproduzierbare, skalare Lauf-Parameter (Kopie).
        risk_notes:       Auditierbare Risiko-/Kontext-Hinweise (immutable).
        safety_flags:     Übernommene/Defaultete Sicherheits-Flags.
    """

    experiment_id: str
    title: str
    strategy_name: str
    starting_equity: float
    ending_equity: float
    number_of_trades: int
    approved_signals: int
    rejected_signals: int
    metrics: dict[str, float]
    parameters: dict[str, str | int | float | bool]
    risk_notes: tuple[str, ...]
    safety_flags: dict[str, bool]


def summarize_backtest_result(
    result: BacktestResult, title: str = "Liquent Backtest"
) -> BacktestExperimentSummary:
    """Überführt ein ``BacktestResult`` in eine ``BacktestExperimentSummary``.

    Reine Funktion. Sicherheits-Flags werden aus ``result.parameters``
    übernommen; fehlt ein Flag, wird es defensiv auf ``False`` gesetzt und ein
    entsprechender Hinweis in ``risk_notes`` ergänzt (Audit-Transparenz).
    """
    strategy_name = str(result.parameters.get("strategy", "unknown"))

    safety_flags: dict[str, bool] = {}
    missing: list[str] = []
    for name in _SAFETY_FLAG_NAMES:
        if name in result.parameters:
            safety_flags[name] = bool(result.parameters[name])
        else:
            safety_flags[name] = False
            missing.append(name)

    # Auditierbare, deskriptive Risk Notes — abhängig vom Sizing-Modus. Keine
    # Wertung, keine Empfehlung, keine Profitabilitätsaussage.
    gate_note = "Risk Engine gate was applied before every simulated trade."
    rejected_note = "Rejected signals did not produce trades."
    sizing_mode = str(result.parameters.get("sizing_mode", "")).strip()

    if sizing_mode == "percent_risk":
        risk_notes: list[str] = [
            "Percentage risk sizing was used.",
            "A stop_price is required for percent_risk sizing.",
            "Signals without stop_price are rejected by the Risk Engine.",
            gate_note,
            rejected_note,
        ]
    elif sizing_mode == "absolute":
        risk_notes = [
            "Absolute sizing mode was used.",
            gate_note,
            rejected_note,
        ]
    else:
        # Fehlender oder unbekannter Modus -> defensive Audit-Hinweise.
        risk_notes = [
            "Sizing mode was missing or unknown; report uses defensive audit notes.",
            gate_note,
        ]

    # Gemeinsamer, deskriptiver Audit-Hinweis (keine Empfehlung).
    risk_notes.append("Descriptive summary only; this is not investment advice.")

    if missing:
        risk_notes.append(
            "Safety flags "
            + ", ".join(missing)
            + " were missing in parameters and defaulted to False."
        )

    return BacktestExperimentSummary(
        experiment_id=result.experiment_id,
        title=title,
        strategy_name=strategy_name,
        starting_equity=result.starting_equity,
        ending_equity=result.ending_equity,
        number_of_trades=result.number_of_trades,
        approved_signals=result.approved_signals,
        rejected_signals=result.rejected_signals,
        metrics=dict(result.metrics),
        parameters=dict(result.parameters),
        risk_notes=tuple(risk_notes),
        safety_flags=safety_flags,
    )


def _format_value(value: object) -> str:
    """Deterministische, stabile Stringdarstellung eines skalaren Werts."""
    # bool VOR int prüfen (bool ist Subklasse von int) — liefert "True"/"False".
    if isinstance(value, bool):
        return "True" if value else "False"
    return str(value)


def summary_to_markdown(summary: BacktestExperimentSummary) -> str:
    """Erzeugt einen stabilen, deterministischen Markdown-Report.

    Reihenfolge der Abschnitte und Tabellenzeilen ist fix (folgt der
    Einfügereihenfolge der zugrundeliegenden Dicts). Keine Wall-Clock-Zeit,
    keine zufälligen IDs, keine Profitabilitäts- oder Empfehlungsaussagen.
    """
    lines: list[str] = []

    lines.append("# Liquent Backtest Experiment")
    lines.append("")

    lines.append("## Experiment")
    lines.append("")
    lines.append(f"- ID: {summary.experiment_id}")
    lines.append(f"- Title: {summary.title}")
    lines.append(f"- Strategy: {summary.strategy_name}")
    lines.append(f"- Starting Equity: {_format_value(summary.starting_equity)}")
    lines.append(f"- Ending Equity: {_format_value(summary.ending_equity)}")
    lines.append(f"- Number of Trades: {summary.number_of_trades}")
    lines.append(f"- Approved Signals: {summary.approved_signals}")
    lines.append(f"- Rejected Signals: {summary.rejected_signals}")
    lines.append("")

    lines.append("## Metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    for key, value in summary.metrics.items():
        lines.append(f"| {key} | {_format_value(value)} |")
    lines.append("")

    lines.append("## Parameters")
    lines.append("")
    lines.append("| Parameter | Value |")
    lines.append("|---|---|")
    for key, value in summary.parameters.items():
        lines.append(f"| {key} | {_format_value(value)} |")
    lines.append("")

    lines.append("## Risk Notes")
    lines.append("")
    for note in summary.risk_notes:
        lines.append(f"- {note}")
    lines.append("")

    lines.append("## Safety Flags")
    lines.append("")
    lines.append("| Flag | Value |")
    lines.append("|---|---|")
    for name in _SAFETY_FLAG_NAMES:
        # Defensive Absicherung, falls ein Flag fehlt (sollte nicht vorkommen).
        value = summary.safety_flags.get(name, False)
        lines.append(f"| {name} | {_format_value(value)} |")
    lines.append("")

    return "\n".join(lines)


def summary_to_dict(summary: BacktestExperimentSummary) -> dict[str, object]:
    """Wandelt die Summary in ein serialisierbares ``dict`` (reine Datentypen).

    Tupel werden zu Listen, verschachtelte Dicts werden kopiert — geeignet für
    JSON-/YAML-Serialisierung in einer späteren Phase (kein I/O hier).
    """
    return {
        "experiment_id": summary.experiment_id,
        "title": summary.title,
        "strategy_name": summary.strategy_name,
        "starting_equity": summary.starting_equity,
        "ending_equity": summary.ending_equity,
        "number_of_trades": summary.number_of_trades,
        "approved_signals": summary.approved_signals,
        "rejected_signals": summary.rejected_signals,
        "metrics": dict(summary.metrics),
        "parameters": dict(summary.parameters),
        "risk_notes": list(summary.risk_notes),
        "safety_flags": dict(summary.safety_flags),
    }
