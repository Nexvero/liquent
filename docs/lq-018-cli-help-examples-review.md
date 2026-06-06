# LQ-018 — CLI Help and Examples Review

> Status: **Phase 1 — Spezifikation / Dokumentation.** Keine Implementierung,
> keine Code-Änderung in `src/`, keine Echtdaten, keine Report-Dateien. Plant die
> Konsolidierung von CLI-Hilfe, README-Beispielen und Parametererklärungen für
> `backtest_mid_breakout.py`.

## 1. Ausgangslage

- Die CLI `src/liquent/cli/backtest_mid_breakout.py` wurde seit LQ-009 stark
  erweitert: Strategieauswahl (`--strategy v0|v1`), v1-Parameter, Kostenmodell-
  Parameter, Report-Metadata (`strategy_metadata`/`cost_metadata`).
- README und CLI-Hilfe sollen konsistent, verständlich und reproduzierbar sein.
- LQ-017 hat empfohlen, vor neuen Backtesting-Mechaniken die CLI-Doku/UX zu
  konsolidieren.

### ⚠ Verifizierter kritischer Befund (bindend für Phase 2)

**`python -m liquent.cli.backtest_mid_breakout --help` stürzt aktuell ab** mit:

```text
ValueError: unsupported format character ')' (0x29) at index 57
```

Ursache: zwei argparse-Help-Strings enthalten **literale `%`-Zeichen**, die
argparse als Format-Platzhalter (`help % params`) interpretiert:

- Zeile 164 (`--fee-rate`): `"… (0.001 = 0,1 %). >= 0."`
- Zeile 172 (`--slippage`): `"… (0.0005 = 0,05 %). >= 0."`

> **Phase-2-Pflicht:** Diese `%` müssen als `%%` escaped (oder die Stelle
> umformuliert) werden, damit `--help` funktioniert. Damit ist Phase 2 **nicht**
> rein kosmetisch — sie behebt einen echten Bug. Der geplante Test „`--help`
> läuft erfolgreich" (siehe §8.1) ist genau die Regression, die das absichert.

### Aktuelle Parametergruppen (Ist — derzeit ein einzelner, ungruppierter Parser)

- **Input/Datenquelle:** `--csv` (Pflicht), `--output` (Pflicht), `--symbol`,
  `--exchange`, `--asset-class`, `--timeframe`, `--gap-policy`, `--max-gaps`,
  `--history-policy`, `--overwrite`.
- **Strategieauswahl:** `--strategy v0|v1` (Default v0).
- **Gemeinsame Strategieparameter:** `--lookback-bars`, `--stop-distance-pct`,
  `--min-strength`, `--allow-short` (Sentinel-Default, strategieabhängig
  aufgelöst).
- **v1-only Strategieparameter:** `--breakout-threshold-pct`, `--cooldown-bars`,
  `--max-signals-per-day` (bei v0 hart abgelehnt).
- **Risk-/Backtestparameter:** `--initial-equity`, `--risk-per-trade-pct`,
  `--max-position-size`, `--max-total-exposure`, `--max-daily-drawdown`
  (`sizing_mode` ist fix `percent_risk`).
- **Kostenmodell:** `--fee-rate`, `--spread`, `--slippage` (Default `0.0`).
- **Output/Reporting:** `--output`, `--overwrite` (Markdown-Report; Metadaten
  automatisch).

## 2. Ziel

Eine klare CLI-Dokumentation und Hilfe-Struktur:
- verständliche, **funktionierende** Help-Texte in argparse,
- konsistente README-Beispiele,
- klare v0/v1-Abgrenzung und v1-only-Gating-Hinweise,
- klare CostModel-Erklärung,
- **keine** Ergebnisinterpretation, **keine** Trading-Empfehlung.

## 3. Nicht-Ziele

- keine neue CLI-Funktionalität, keine Strategie-/Runner-/RiskEngine-Änderung,
- keine Echtdatenläufe, keine Report-Dateien,
- keine Profitabilitätsbewertung, keine Trading-Empfehlung,
- keine Optimierung/Parameter-Suche,
- keine Exchange-/Live-/Paper-Anbindung.

> Ausnahme vom „keine Logikänderung": der `%`→`%%`-Fix in zwei Help-Strings ist
> ein **Bugfix am Hilfetext** (kein Verhaltens-/Logikwechsel der Auswertung).

## 4. CLI-Help-Struktur

Empfehlung: **argparse `add_argument_group(...)`** einführen, um die Hilfe
lesbarer zu gliedern — **ohne** Logik/Defaults/Validierung zu ändern. Gruppen:

- `Data input`
- `Strategy selection`
- `Strategy parameters` (gemeinsam)
- `Strategy v1 parameters`
- `Risk / Backtest parameters`
- `Cost model`
- `Output / Reporting`

```python
g_data = parser.add_argument_group("Data input")
g_strat = parser.add_argument_group("Strategy selection")
g_v1 = parser.add_argument_group("Strategy v1 parameters")
g_cost = parser.add_argument_group("Cost model")
# … bestehende add_argument-Aufrufe nur in die Gruppen verschieben (gleiche Flags/Defaults).
```

> Rein organisatorisch: dieselben Flags, Defaults, `dest`, Validierung. Nur die
> Help-Darstellung wird gegliedert.

## 5. Parameter-Erklärungen (gewünschte Help-Texte)

**Strategie:**
- `--strategy v0|v1` — „Strategy version to use. Default: v0 for
  backward-compatible runs."

**Gemeinsam:**
- `--lookback-bars` — „Number of previous bars used for the breakout window.
  Defaults depend on strategy (v0: 3, v1: 12)."
- `--stop-distance-pct` — „Relative stop distance used for percent-risk sizing.
  In the current runner, stop_price is used for sizing, not as an executed
  stop-loss."
- `--min-strength` — „Minimum signal strength filter. Default: 0.0."

**v1-only:**
- `--breakout-threshold-pct` — „Minimum relative breakout distance for v1. Only
  valid with --strategy v1."
- `--cooldown-bars` — „Number of bars skipped after an emitted v1 signal. Only
  valid with --strategy v1."
- `--max-signals-per-day` — „Optional max number of v1 signals per UTC day. Only
  valid with --strategy v1. Omit to disable."

**Cost model** (Prozentangaben in den Help-Texten als `%%` escapen!):
- `--fee-rate` — „Fee rate as notional fraction (e.g. 0.001 = 0.1%%).
  Default: 0.0."
- `--spread` — „Absolute spread cost per unit. Default: 0.0."
- `--slippage` — „Slippage as notional fraction (e.g. 0.0005 = 0.05%%).
  Default: 0.0."

> **Keine** Formulierungen wie „besser", „profitabel", „empfohlen".

## 6. README-Beispiele

Mit **Platzhalterpfaden** (keine echten Datenpfade), ohne Ergebnisinterpretation:

1. Rückwärtskompatibler v0-Lauf:
   ```bash
   python -m liquent.cli.backtest_mid_breakout --strategy v0 \
     --csv PATH/TO/data.csv --output reports/out_v0.md --overwrite
   ```
2. v1 mit Threshold/Cooldown:
   ```bash
   python -m liquent.cli.backtest_mid_breakout --strategy v1 \
     --breakout-threshold-pct 0.001 --cooldown-bars 3 \
     --csv PATH/TO/data.csv --output reports/out_v1.md --overwrite
   ```
3. v1 mit `max_signals_per_day`:
   ```bash
   python -m liquent.cli.backtest_mid_breakout --strategy v1 \
     --max-signals-per-day 2 \
     --csv PATH/TO/data.csv --output reports/out_v1_limit.md --overwrite
   ```
4. Lauf mit Kostenmodell:
   ```bash
   python -m liquent.cli.backtest_mid_breakout --strategy v1 \
     --fee-rate 0.001 --spread 0.0 --slippage 0.0005 \
     --csv PATH/TO/data.csv --output reports/out_costs.md --overwrite
   ```

> Reports landen unter `reports/` (git-ignoriert). Keine Echtdaten-Referenz,
> keine Profitabilitätsaussage.

## 7. Validierungs-/Gating-Hinweise (in README + Hilfe klarstellen)

- Default-Strategie ist **v0**.
- v1-only Parameter sind **ohne `--strategy v1` ungültig** (auch bei Default-v0).
- v1-only: `--breakout-threshold-pct`, `--cooldown-bars`,
  `--max-signals-per-day`.
- Negative Kostenparameter (`--fee-rate/--spread/--slippage < 0`) sind ungültig.
- `--max-signals-per-day` muss `> 0` sein, wenn gesetzt; **Weglassen = `None` =
  deaktiviert**.

## 8. Tests für Phase 2

1. `--help` **läuft erfolgreich** (Exit 0 / kein Traceback) — deckt den
   `%`-Bug ab.
2. Help enthält `--strategy`.
3. Help enthält `--breakout-threshold-pct`.
4. Help enthält `--cooldown-bars`.
5. Help enthält `--max-signals-per-day`.
6. Help enthält `--fee-rate`, `--spread`, `--slippage`.
7. Help weist auf den v0-Default hin.
8. Help weist auf v1-only Parameter hin.
9. Help enthält **keine** Bewertungs-/Profitabilitätsbegriffe
   (`profitable`, `better`, `worse`, `winner`, `recommended`).
10. README enthält konsistente CLI-Beispiele (mit Platzhalterpfaden).
11. Bestehende Tests bleiben grün.

> Optional (§10.4): **keine** Snapshot-Tests des kompletten Help-Texts — nur
> robuste Substring-Checks, damit die Tests nicht fragil werden.

## 9. Kompatibilität

- **Keine** Änderung an CLI-Logik, Defaults, `dest`-Namen oder Validierung.
- **Keine** Änderung an Strategie/Runner/RiskEngine.
- Nur Help-Texte, argparse-Gruppierung, der `%`→`%%`-Bugfix und README-Doku.
- **Bestehende CLI-Aufrufe bleiben unverändert gültig** (alle Bestandstests
  grün; Argument-Gruppen ändern das Parsing nicht).

## 10. Offene Entscheidungspunkte

1. **argparse in Gruppen strukturieren?**
   → *Empfehlung: ja* (ohne Risiko, nur Darstellung).
2. **README: vollständige Parameter-Tabelle?**
   → *Empfehlung: kompakt ja.*
3. **Separate CLI-Reference-Doku unter `docs/`?**
   → *Empfehlung: ja*, falls README sonst zu lang wird (z. B.
   `docs/cli-reference.md`).
4. **Help-Text-Testdatei?**
   → *Empfehlung: ja*, klein und robust (Substring-Checks, kein Snapshot).
5. **Beispiele mit echten Projektpfaden?**
   → *Empfehlung: nein*, nur Platzhalter.

---

## Phase 2 Implementation Status

Umgesetzt (nur Hilfe/Darstellung/Doku — keine Logik-/Default-Änderung):

- **Help-Bug `%`→`%%` behoben:** die `--fee-rate`/`--slippage`-Help-Texte
  escapen Prozentangaben nun (`0.1%%`/`0.05%%`); **`--help` läuft mit Exit 0**.
- **argparse-Gruppen** ergänzt: `Data input`, `Strategy selection`,
  `Strategy parameters`, `Strategy v1 parameters`, `Risk / Backtest`,
  `Cost model`, `Output / Reporting` — rein organisatorisch, gleiche Flags/
  Defaults/`dest`/`choices`/`required`/Validierung.
- **Help-Texte konsolidiert** (englisch, neutral; keine Bewertungs-/Profitabilitäts-
  begriffe). Hinweis bei `--stop-distance-pct`: stop_price dient nur dem Sizing,
  kein ausgeführter Stop-Loss.
- **README-Beispiele** ergänzt: v0, v1 (Threshold/Cooldown), v1 mit
  `--max-signals-per-day`, Lauf mit Kostenmodell — **Platzhalterpfade**, kein
  Echtdatenbezug, keine Ergebnisinterpretation; `--help`-Hinweis ergänzt.
- **Tests:** `tests/test_cli_help.py` (8) — `--help` Exit 0, zentrale Flags,
  v0-Default-Hinweis, v1-only-Hinweis, Cost-Model-Hinweise, keine
  Bewertungsbegriffe, argparse-Gruppen, README-Beispiele. Bestehende Tests grün.
- **Keine Logikänderung, keine Default-Änderung, keine Echtdaten.**
- **pytest: 353 passed** (lokale `.venv`).

Runner/RiskEngine/CostModel/Strategien unverändert. Kein Push.

---

*Research-/Backtesting-Kontext. Keine Live-/Paper-Trading-Funktion, keine
Exchange-Anbindung, keine Profitabilitätsaussage, keine Handelsempfehlung.*
