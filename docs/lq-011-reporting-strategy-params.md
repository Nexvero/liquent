# LQ-011 — Reporting strategy_params

> Status: **Phase 1 — Spezifikation / Dokumentation.** Keine Implementierung,
> keine Code-Änderung in `src/`. Dieses Dokument plant, wie Backtest-Reports
> künftig die verwendete Strategie und ihre **effektiven** Parameter eindeutig,
> deterministisch und (perspektivisch) maschinenlesbar dokumentieren.

## 1. Ausgangslage

- Seit **LQ-009** kann die CLI (`src/liquent/cli/backtest_mid_breakout.py`)
  zwischen v0 (`MidBreakoutStrategy`) und v1 (`MidBreakoutStrategyV1`) wählen
  (`--strategy v0|v1`); gemeinsame Parameter werden per Sentinel-Logik
  strategieabhängig **aufgelöst**.
- Der **Terminal-Hinweis** (`strategy: …`-Zeile auf stdout) zeigt Strategie +
  effektive Parameter bereits an — aber **nur** flüchtig auf der Konsole, nicht
  im Report.
- Der **Markdown-Report** trägt aktuell:
  - im Abschnitt „## Experiment" die Zeile `- Strategy: <Klassenname>`
    (aus `summary.strategy_name`),
  - im Abschnitt „## Parameters" u. a. die Zeile `| strategy | <Klassenname> |`
    sowie `| signals_total | … |` (aus `result.parameters`).
- **Verifizierte Lücke:** Die Strategie-**Tuning-Parameter** (`lookback_bars`,
  `stop_distance_pct`, `breakout_threshold_pct`, `cooldown_bars`, `allow_short`,
  `min_strength`) stehen **nicht** im Report. `BacktestRunner` schreibt in
  `result.parameters` nur Risk-/Cost-/Daten-/Modus-Felder, den Strategie-
  **Klassennamen** (`type(self.strategy).__name__`) und `signals_total` — aber
  keine strategie-spezifischen Werte. Diese sind nur der **CLI** bekannt (nach
  Sentinel-Auflösung).
- Für spätere kontrollierte Vergleiche (z. B. LQ-010) müssen Reports **eindeutig
  reproduzierbar** sein und die effektiven Parameter explizit ausweisen.

### Verifizierte Reporting-Struktur (`src/liquent/backtesting/reporting.py`)

- `BacktestExperimentSummary` — frozen dataclass; alle Felder aktuell Pflicht.
- `summarize_backtest_result(result, title="…") -> BacktestExperimentSummary`
  — reine Funktion; baut Summary aus `result`.
- `summary_to_markdown(summary) -> str` — feste Abschnittsreihenfolge:
  `# Experiment → ## Metrics → ## Parameters → ## Risk Notes → ## Safety Flags`.
- `summary_to_dict(summary) -> dict` — JSON-fähige Sicht.
- **Determinismus-Invarianten:** feste Reihenfolge (Dict-Einfügereihenfolge),
  Skalar-Formatierung über `_format_value` (`bool → "True"/"False"`), keine
  Wall-Clock, keine Zufalls-IDs.
- **Typ-Constraint:** `parameters` ist `dict[str, str | int | float | bool]`
  (nur Skalare). **Ein verschachteltes `strategy_params` darf NICHT in
  `parameters` abgelegt werden** — es braucht ein eigenes Summary-Feld.

## 2. Ziel

Reports sollen künftig eindeutig enthalten:

- `strategy_key`: `"v0"` oder `"v1"`
- `strategy_name`: `"MidBreakoutStrategy"` oder `"MidBreakoutStrategyV1"`
- `strategy_params`: Mapping der **effektiv verwendeten** Parameter
- optional: `strategy_family`: `"mid_breakout"`

Konzeptuelle Struktur (Beispiel v1):

```text
strategy:
  family: mid_breakout
  key: v1
  name: MidBreakoutStrategyV1
  params:
    lookback_bars: 12
    stop_distance_pct: 0.01
    breakout_threshold_pct: 0.001
    cooldown_bars: 3
    allow_short: true
    min_strength: 0.0
```

Beispiel v0:

```text
strategy:
  family: mid_breakout
  key: v0
  name: MidBreakoutStrategy
  params:
    lookback_bars: 3
    stop_distance_pct: 0.05
    allow_short: true
    min_strength: 0.0
```

## 3. Nicht-Ziele

- keine Profitabilitätsbewertung,
- keine Trading-Empfehlung,
- keine Echtdatenläufe,
- keine Report-Artefakte committen,
- keine Live-/Paper-/Exchange-Anbindung,
- keine Optimierung, keine Parameter-Suche,
- keine Runner-Logikänderung,
- keine RiskEngine-Änderung.

## 4. Design-Entscheidung

**Variante A — CLI baut `strategy_metadata` und übergibt es ans Reporting.**
Die CLI kennt nach der Sentinel-Auflösung bereits alle effektiven Werte; sie
stellt ein explizites `strategy_metadata`-Dict zusammen und reicht es an
`summarize_backtest_result` durch.

- *Pro:* keine Strategieänderung, keine Runner-/RiskEngine-Änderung, minimales
  Risiko, effektive Werte sind dort bereits bekannt, passt zu LQ-009.
- *Contra:* andere Entry Points (außer der CLI) müssten das Metadaten-Dict selbst
  bauen.

**Variante B — Strategien erhalten eine introspektive API** (z. B.
`strategy.describe()` oder `strategy.params`).

- *Pro:* sauberer für mehrere Entry Points; Single Source of Truth in der
  Strategieklasse.
- *Contra:* **verändert die Strategieklassen** (v0/v1) und braucht zusätzliche
  Tests; höheres Risiko, widerspricht „Strategien nicht ändern" der laufenden
  Phasen.

> **Empfehlung für Phase 2: Variante A.** Begründung: keine Strategieänderung,
> keine Runner-/RiskEngine-Änderung, geringes Risiko, CLI kennt die effektiven
> Werte bereits. Variante B bleibt als spätere Option dokumentiert (wenn mehrere
> Entry Points entstehen).

## 5. Zielstruktur im Report

Da `parameters` skalar-typisiert ist, wird `strategy_metadata` als **eigenes,
optionales Summary-Feld** geführt (nicht in `parameters` gemischt). Der
Markdown-Report erhält **additiv** einen neuen Abschnitt direkt nach
„## Experiment" (vor „## Metrics"), nur wenn Metadaten vorhanden sind:

```markdown
## Strategy

| Field  | Value                 |
| ------ | --------------------- |
| family | mid_breakout          |
| key    | v1                    |
| name   | MidBreakoutStrategyV1 |

### Strategy Parameters

| Parameter              | Value |
| ---------------------- | ----- |
| lookback_bars          | 12    |
| stop_distance_pct      | 0.01  |
| breakout_threshold_pct | 0.001 |
| cooldown_bars          | 3     |
| allow_short            | True  |
| min_strength           | 0.0   |
```

Regeln:
- **Additiv:** bestehende Abschnitte (Experiment/Metrics/Parameters/Risk
  Notes/Safety Flags) bleiben unverändert; die bestehende `| strategy | … |`-
  Zeile in „## Parameters" bleibt erhalten (nicht ersetzen).
- **Deterministisch:** `params` ist ein **insertion-ordered** Dict mit fester
  Reihenfolge (v0: `lookback_bars, stop_distance_pct, allow_short, min_strength`;
  v1: zusätzlich `breakout_threshold_pct, cooldown_bars` an spezifizierter
  Position). Werte über das bestehende `_format_value` (bool → `True`/`False`).
- **Backward-compatible:** Fehlt `strategy_metadata` (Default `None`), wird der
  neue Abschnitt **nicht** gerendert → bestehende Reports/Tests bleiben
  byte-identisch.

## 6. CLI-Integration (Plan für Phase 2)

Nach der Sentinel-Auflösung in `backtest_mid_breakout.py` (Strategie ist bereits
instanziiert, effektive Werte stehen in `args`):

```python
params = {
    "lookback_bars": args.lookback_bars,
    "stop_distance_pct": args.stop_distance_pct,
    "allow_short": args.allow_short,
    "min_strength": args.min_strength,
}
if args.strategy == "v1":
    # an spezifizierter Position einfügen (deterministische Reihenfolge)
    params = {
        "lookback_bars": args.lookback_bars,
        "stop_distance_pct": args.stop_distance_pct,
        "breakout_threshold_pct": args.breakout_threshold_pct,
        "cooldown_bars": args.cooldown_bars,
        "allow_short": args.allow_short,
        "min_strength": args.min_strength,
    }

strategy_metadata = {
    "family": "mid_breakout",
    "key": args.strategy,                 # "v0" | "v1"
    "name": type(strategy).__name__,      # MidBreakoutStrategy | …V1
    "params": params,
}
summary = summarize_backtest_result(
    result, title="Liquent MidBreakout Backtest",
    strategy_metadata=strategy_metadata,
)
```

- Für **v0** nur v0-relevante Parameter (keine v1-only Felder).
- Für **v1** zusätzlich `breakout_threshold_pct` und `cooldown_bars`.
- **`max_signals_per_day` NICHT aufnehmen**, solange nicht aktiv implementiert —
  um keine aktive Funktion vorzutäuschen (Entscheidungspunkt 2).

## 7. Tests für Phase 2

1. v0-Report enthält `strategy` `key` `v0`.
2. v0-Report enthält `MidBreakoutStrategy`.
3. v0-Report enthält `lookback_bars`, `stop_distance_pct`, `allow_short`,
   `min_strength`.
4. v0-Report enthält **keine** v1-only Parameter
   (`breakout_threshold_pct`/`cooldown_bars`) im Strategy-Parameters-Abschnitt.
5. v1-Report enthält `strategy` `key` `v1`.
6. v1-Report enthält `MidBreakoutStrategyV1`.
7. v1-Report enthält `breakout_threshold_pct` und `cooldown_bars`.
8. v1-Report enthält die **effektiv aufgelösten Defaults** (12 / 0.01 / 0.001 /
   3), wenn keine Parameter explizit gesetzt wurden.
9. v1-Report enthält **explizit überschriebene** Werte, wenn CLI-Parameter
   gesetzt wurden.
10. Bestehende Reporting-Tests bleiben grün (Report ohne `strategy_metadata`
    bleibt byte-identisch).
11. Keine Reports committed (Tests nutzen `tmp_path`).
12. Keine Netzwerk-/Live-/Paper-Trading-Pfade (statischer Scan).

## 8. Kompatibilität

- Bestehende Reports bleiben erzeugbar; neue Felder sind **additiv**.
- Bestehende Tests dürfen nicht brechen — `strategy_metadata` ist **optional**
  mit Default `None`; ohne Angabe ändert sich der Output nicht.
- Keine Änderung an der Backtest-Result-Kernlogik (`runner.py` bleibt
  unverändert) — die Metadaten kommen aus der CLI, nicht aus dem Runner.
- Signaturerweiterung als optionaler Parameter mit Default `None`:

  ```python
  summarize_backtest_result(
      result, title="Liquent Backtest", *, strategy_metadata: dict | None = None
  )
  ```

  und additives, optionales Feld `strategy_metadata: dict | None = None` auf
  `BacktestExperimentSummary` (Default-Feld am Ende der frozen dataclass).
  `summary_to_dict` ergänzt einen Schlüssel `"strategy"` **nur**, wenn Metadaten
  vorhanden sind (sonst unverändert → bestehende Dict-Tests bleiben grün).

## 9. Offene Entscheidungspunkte

1. **Nur Markdown oder später auch JSON/structured output?**
   → *Empfehlung: zunächst Markdown/aktueller Report*; `strategy_metadata` so
   strukturieren (family/key/name/params), dass `summary_to_dict`/JSON später
   trivial möglich ist.
2. **`max_signals_per_day` als `None` im v1-Report zeigen?**
   → *Empfehlung: nein*, solange nicht aktiv (keine Scheinfunktion).
3. **`strategy_params` aus CLI oder aus Strategieklassen?**
   → *Empfehlung: Phase 2 aus CLI* (Variante A).
4. **Terminal-Hinweis und Report denselben Formatter nutzen?**
   → *Empfehlung: später möglich*; Phase 2 minimal halten (kein gemeinsamer
   Formatter-Refactor jetzt).
5. **(Verifiziert) Ablageort:** `strategy_params` als **eigenes Summary-Feld**,
   NICHT in `parameters` (dort nur Skalare erlaubt). → festgelegt in §5/§8.

---

## Phase 2 Implementation Status

Umgesetzt (Variante A, additiv, backward-compatible):

- **`strategy_metadata` implementiert** als optionaler, keyword-only Parameter
  von `summarize_backtest_result(result, title=…, *, strategy_metadata=None)`.
- **`BacktestResult.parameters` bleibt skalar** (`runner.py` unverändert) — die
  Metadaten liegen NICHT in `parameters`.
- **Separates Summary-Feld:** `BacktestExperimentSummary.strategy_metadata`
  (additiv, Default `None`). Normalisiert auf feste Reihenfolge
  `family, key, name, params` (deterministisch, `params` defensiv kopiert).
- **CLI baut metadata aus effektiven Parametern** (nach Sentinel-Auflösung) in
  `backtest_mid_breakout.py`: v0 → `lookback_bars, stop_distance_pct,
  allow_short, min_strength`; v1 zusätzlich `breakout_threshold_pct,
  cooldown_bars`. `max_signals_per_day` bewusst **nicht** aufgenommen.
- **Markdown-Report** enthält den Abschnitt `## Strategy` + `### Strategy
  Parameters` **nur** bei vorhandener `strategy_metadata` (sonst byte-identisch
  zu vorher). Eingefügt nach `## Experiment`, vor `## Metrics`.
- **`summary_to_dict`** ergänzt den Schlüssel `"strategy"` **nur** bei
  vorhandener metadata.
- **Tests:** `tests/test_reporting_strategy_metadata.py` (9 Tests; Reporting
  isoliert + CLI über `main` + `tmp_path`). Bestehende Reporting-/CLI-/Strategie-
  Tests bleiben grün.
- **pytest: 278 passed** (lokale `.venv`).
- Runner/RiskEngine/v0-/v1-Strategie unverändert. Kein Push.

Hinweis (statischer Scan): `paper_trading`/`live_execution`/`network_calls` sind
im Reporting legitime **Safety-Flag-Namen** (dokumentieren deren Abwesenheit) und
daher in der Verbotsliste des Reporting-Scans bewusst ausgenommen.

Keine Profitabilitätsaussage, keine Echtdatenbewertung.

---

*Research-/Backtesting-Kontext. Keine Live-/Paper-Trading-Funktion, keine
Exchange-Anbindung, keine Profitabilitätsaussage, keine Handelsempfehlung.*
