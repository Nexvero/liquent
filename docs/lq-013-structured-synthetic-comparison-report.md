# LQ-013 — Structured Synthetic Comparison Report

> Status: **Phase 1 — Spezifikation / Dokumentation.** Keine Implementierung,
> keine Code-Änderung in `src/`, kein Echtdatenlauf. Dieses Dokument plant einen
> strukturierten, rein **technischen** Vergleichsreport für **synthetische**
> v0/v1-Läufe. Keine Bewertung, keine Empfehlung, keine Profitabilitätsaussage.

## 1. Ausgangslage

- **LQ-008** hat `MidBreakoutStrategyV1` additiv eingeführt.
- **LQ-009** hat die CLI-Strategieauswahl (`--strategy v0|v1`) eingeführt.
- **LQ-010** hat synthetische v0/v1-Vergleichstests eingeführt
  (`tests/test_synthetic_strategy_comparison.py`, deterministische Serien
  `_MICRO_LONG`, `_MICRO_SHORT`, `_STAIR`).
- **LQ-011** hat `strategy_metadata` im Reporting eingeführt.
- **LQ-012** hat `cost_metadata` im Reporting eingeführt.
- Es gibt aktuell **technische Einzelreports** (`summary_to_markdown` /
  `summary_to_dict`), aber **keinen strukturierten Vergleichsreport**, der
  mehrere Backtest-/Signal-Ergebnisse **nebeneinander** stellt.

### Verifizierte wiederverwendbare Bausteine

- `src/liquent/backtesting/reporting.py` enthält bereits:
  - `_format_value` (deterministische Skalar-/Bool-Formatierung),
  - `_normalize_strategy_metadata`, `_normalize_cost_metadata`, `_COST_FIELDS`,
  - durchgängig deterministisches Markdown (feste Reihenfolge, keine Wall-Clock).
- Die **technischen Kennzahlen** je Variante stammen aus einem `BacktestResult`:
  - `result.parameters["signals_total"]` → `signals_total`,
  - `result.approved_signals` → `approved_signals`,
  - `result.rejected_signals` → `rejected_signals`,
  - `result.number_of_trades` → `trades_total`.

Der Vergleich dokumentiert **nur** technische Unterschiede: `signals_total`,
`trades_total`, `approved_signals`, `rejected_signals`, `strategy_metadata`,
`cost_metadata`, technische Parameter, synthetischer Datensatz. **Keine**
Bewertung, **kein** Ranking, **keine** Empfehlung, **keine** Profitabilität.

## 2. Ziel

Ein **strukturierter Vergleichsreport** für synthetische Läufe, der mehrere
Varianten nebeneinanderstellt, z. B.:

- v0 frictionless,
- v1 frictionless,
- v1 mit anderem `threshold`/`cooldown`,
- optional v1 mit `CostModel`-Werten.

Reproduzierbar dokumentiert werden:

- `dataset_name`, `dataset_type: synthetic`, `dataset_description`,
- `variants` mit je: technische Kennzahlen, `strategy_metadata`,
  `cost_metadata`, technische Parameter.

**`generated_at` wird vermieden** (oder nur deterministisch via explizit
übergebenem Wert) — deterministische Tests haben Vorrang (siehe §10.2).

## 3. Nicht-Ziele

- keine Echtdaten, kein Download, keine Exchange-API,
- kein Paper-Trading, kein Live-Trading,
- keine Profitabilitätsbewertung, keine Trading-Empfehlung,
- keine Optimierung, keine Parameter-Suche,
- keine Walk-forward-Analyse, keine Out-of-sample-Aussage,
- **keine** automatischen Reports unter `reports/` committen,
- kein Deployment.

## 4. Vorgeschlagene Datenstruktur

Eine interne, **normalisierte** Vergleichsform (reine Datentypen, deterministisch):

```python
comparison = {
    "title": "Synthetic MidBreakout v0/v1 comparison",
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
                "params": {...},
            },
            "cost_model": {"fee_rate": 0.0, "spread": 0.0, "slippage": 0.0},
            "technical_results": {
                "signals_total": 2,
                "trades_total": 2,
                "approved_signals": 2,
                "rejected_signals": 0,
            },
        },
        {"label": "v1", "...": "..."},
    ],
    "notes": [
        "Synthetic data only.",
        "No profitability assessment.",
        "No trading recommendation.",
    ],
}
```

Regeln:
- **Keine Interpretation** (besser/schlechter), **kein Ranking**, **keine
  Empfehlung**.
- `strategy` / `cost_model` werden mit den bestehenden Normalisierern
  (`_normalize_strategy_metadata` / `_normalize_cost_metadata`) in feste
  Reihenfolge gebracht, damit der Vergleich byte-stabil ist.
- `technical_results` enthält ausschließlich die vier verifizierten Felder
  (s. §1) — **kein** `ending_equity` (siehe §10.3).

## 5. Markdown-Ausgabe

Ein generierbarer Markdown-Vergleichsreport — **nur als Funktions-/Testausgabe**,
**nicht** als zu committender Laufreport (kein Artefakt unter `reports/`).

Beispielstruktur:

```markdown
# Synthetic Strategy Comparison

## Dataset

| Field | Value               |
| ----- | ------------------- |
| name  | micro_breakout_long |
| type  | synthetic           |
| bars  | 18                  |

## Variants

| Variant | Strategy              | Signals | Trades | Approved | Rejected |
| ------- | --------------------- | ------: | -----: | -------: | -------: |
| v0      | MidBreakoutStrategy   |       2 |      2 |        2 |        0 |
| v1      | MidBreakoutStrategyV1 |       1 |      1 |        1 |        0 |

## Variant Parameters

### v0

Strategy:

- family: mid_breakout
- key: v0
- name: MidBreakoutStrategy
- params: lookback_bars=3, stop_distance_pct=0.05, allow_short=True, min_strength=0.0

Cost Model:

- fee_rate: 0.0
- spread: 0.0
- slippage: 0.0

### v1

Strategy:

- ...

Cost Model:

- ...

## Notes

- Synthetic data only.
- No profitability assessment.
- No trading recommendation.
```

Determinismus: feste Abschnitts-/Spaltenreihenfolge, `_format_value` für Werte,
keine Wall-Clock, kein Zufall.

## 6. Technische Integration

**Variante A — neue Funktion in `reporting.py`**
(`render_comparison_markdown(comparison) -> str`).
- *Pro:* zentral, leicht testbar, kein Runner-/RiskEngine-Eingriff.
- *Contra:* `reporting.py` wächst weiter (LQ-011/LQ-012 haben es bereits
  zweimal erweitert).

**Variante B — neues Modul `src/liquent/backtesting/comparison_reporting.py`**.
- *Pro:* klare Trennung Einzelreport vs. Vergleichsreport; besser erweiterbar;
  keine Breaking Changes an `reporting.py`.
- *Contra:* neues Modul.

> **Empfehlung: Variante B — neues Modul
> `src/liquent/backtesting/comparison_reporting.py`.** Begründung: `reporting.py`
> wurde bereits in LQ-011/LQ-012 erweitert; der Vergleichsreport ist ein anderes
> Konzept als der Einzelreport; additiv, keine Breaking Changes. Gemeinsame
> Helfer (`_format_value`, Normalisierer) können aus `reporting.py` importiert
> oder dort zu öffentlichen Helfern erhoben werden (Entscheidung in Phase 2; ein
> einfacher Import des bestehenden `_format_value` genügt zunächst).

Geplante öffentliche API (Phase 2):

```python
# comparison_reporting.py
def build_comparison(title, dataset, variants, notes=None) -> dict: ...
def render_comparison_markdown(comparison: dict) -> str: ...
def comparison_to_dict(comparison: dict) -> dict: ...     # optional (§10.1)

def variant_from_result(label, result, strategy_metadata, cost_metadata) -> dict:
    """Baut eine Variante aus einem BacktestResult + Metadaten (technical_results
    aus signals_total/approved/rejected/number_of_trades)."""
```

## 7. Teststrategie für Phase 2

1. Vergleichsreport rendert den Dataset-Abschnitt.
2. Vergleichsreport rendert die Varianten-Tabelle.
3. v0/v1 Strategie-Metadaten erscheinen korrekt.
4. CostModel-Metadaten erscheinen korrekt.
5. technische Kennzahlen (signals/trades/approved/rejected) erscheinen korrekt.
6. Notes enthalten explizit: „Synthetic data only.", „No profitability
   assessment.", „No trading recommendation.".
7. Ausgabe ist deterministisch (zwei Läufe → byte-identisch).
8. Fehlende optionale Felder werden stabil behandelt (z. B. ohne
   `description`/`bars`, ohne `cost_model`).
9. Keine Report-Dateien werden committed (Tests nutzen ggf. `tmp_path`; primär
   reine String-/Dict-Assertions).
10. Keine Netzwerk-/Live-/Paper-Trading-Pfade (statischer Scan).
11. Bestehende Tests bleiben grün.

Optional:
12. Vergleichsdaten aus den bestehenden synthetischen Serien erzeugen (über echte
    `BacktestRunner`-Läufe in-memory, analog LQ-010) — **ohne** Fixtures zu
    extrahieren, falls das Phase 2 zu groß macht (dann synthetische Kennzahlen
    direkt im Test setzen).

## 8. CLI-Frage

LQ-013 **Phase 2 erzeugt KEINE neue CLI**, außer es wird explizit anders
entschieden.

> Empfehlung:
> - Phase 2: nur Reporting-Modul + Tests.
> - Phase 3: Doku + Commit.
> - Später optional: ein CLI-Befehl für den Vergleichsreport.
>
> Begründung: kein Report-Artefakt, keine komplexe Eingabe, Fokus auf
> strukturierte Darstellung.

## 9. Kompatibilität

- Keine Änderung an bestehenden Reports (`summary_to_markdown`/`_to_dict`).
- Keine Änderung an `BacktestResult`.
- Keine Änderung an `BacktestRunner`.
- Keine Änderung an `RiskEngine`.
- Kein Einfluss auf den CLI-Backtest.
- **Additives Modul** (`comparison_reporting.py`); optional ein additiver Import
  von `_format_value` aus `reporting.py` (keine Signaturänderung dort).

## 10. Offene Entscheidungspunkte

1. **Nur Markdown oder auch Dict/JSON?**
   → *Empfehlung: zunächst Dict-Normalisierung (`build_comparison`) +
   Markdown-Renderer; JSON (`comparison_to_dict`) später trivial möglich.*
2. **`generated_at` enthalten?**
   → *Empfehlung: nein bzw. nur optional als explizit übergebener Wert* —
   deterministische Tests haben Vorrang (Wall-Clock ist in Liquent generell
   tabu).
3. **`ending_equity` aufnehmen?**
   → *Empfehlung: vorerst nein* — vermeidet Ergebnis-Interpretation. Falls
   später doch, nur als rein mechanisches, unkommentiertes Feld.
4. **Vergleichsreport später über CLI?**
   → *Empfehlung: später, nicht in Phase 2.*
5. **Wiederverwendbare synthetische Dataset-Builder?**
   → *Empfehlung: später*, falls mehrere Vergleichsreports folgen (dann ggf.
   die LQ-010-Serien in einen gemeinsamen Test-Helfer heben).
6. **(Verifiziert) Gemeinsame Helfer:** `_format_value`/Normalisierer in
   `reporting.py` sind aktuell „privat" (Unterstrich). → In Phase 2 entweder
   importieren (pragmatisch) oder zu öffentlichen Helfern erheben (sauberer);
   Entscheidung in Phase 2.

---

## Phase 2 Implementation Status

Umgesetzt (Variante B, additiv, keine CLI):

- **Neues Modul `src/liquent/backtesting/comparison_reporting.py`** — isoliert,
  rein, deterministisch; `reporting.py` **unverändert** (eigene kleine lokale
  `_format_value`-Kopie statt Kopplung an ein privates Symbol).
- **`normalize_comparison(comparison)`** implementiert — stabilisiert die
  Eingabe, füllt fehlende optionale Felder mit Defaults, erzwingt feste
  Feldreihenfolgen (`dataset`: name/type/bars/description; Strategy-Kopf:
  family/key/name; Cost: fee_rate/spread/slippage; Results: signals_total/
  trades_total/approved_signals/rejected_signals). `params` bleiben in
  Einfügereihenfolge. Default-Variant-Label `variant_<i>`.
- **`render_comparison_markdown(comparison)`** implementiert — gibt **nur einen
  String** zurück, schreibt **keine** Datei. Abschnitte: `# Title` → `## Dataset`
  → `## Variants` (Übersichtstabelle) → `## Variant Parameters` (Strategy- +
  Cost-Tabellen je Variante) → `## Notes`.
- **Kein CLI**, **keine Reportdateien**, **keine Echtdaten**, **kein**
  `ending_equity`, **kein** `generated_at`, **kein** Ranking/„winner"/„besser".
- **Pflicht-Notes** als Default, wenn nicht gesetzt: „Synthetic data only.",
  „No profitability assessment.", „No trading recommendation.".
- **Export** additiv in `src/liquent/backtesting/__init__.py`
  (`normalize_comparison`, `render_comparison_markdown`).
- **Tests:** `tests/test_comparison_reporting.py` (12). Bestehende Tests grün.
- **pytest: 307 passed** (lokale `.venv`).

Runner/RiskEngine/CLI/v0-/v1-Strategie unverändert. Kein Push.

Keine Profitabilitätsaussage, keine Echtdatenbewertung.

---

*Research-/Backtesting-Kontext. Keine Live-/Paper-Trading-Funktion, keine
Exchange-Anbindung, keine Profitabilitätsaussage, keine Handelsempfehlung.*
