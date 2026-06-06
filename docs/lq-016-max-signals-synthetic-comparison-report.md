# LQ-016 — Synthetic Comparison Report for max_signals_per_day

> Status: **Phase 1 — Spezifikation / Dokumentation.** Keine Implementierung,
> keine Code-Änderung in `src/`, keine Echtdaten, keine Report-Dateien. Plant
> einen kontrollierten **synthetischen** Vergleich, der die technische Wirkung
> von `max_signals_per_day` im strukturierten Comparison-Report sichtbar macht.

## 1. Ausgangslage

- **LQ-013** hat ein isoliertes Comparison-Reporting-Modul eingeführt
  (`src/liquent/backtesting/comparison_reporting.py`:
  `normalize_comparison`, `render_comparison_markdown`).
- **LQ-014** hat synthetische Dataset-Builder eingeführt
  (`tests/helpers/synthetic_data.py`: `build_stair_breakout_for_cooldown` u. a.,
  `InMemoryMarketDataSource`).
- **LQ-015** hat `max_signals_per_day` in `MidBreakoutStrategyV1` **aktiv**
  umgesetzt (UTC-Tageslimit) und über die CLI steuerbar gemacht.
- Es fehlt ein **kontrollierter synthetischer Vergleich**, der `max_signals_per_day`
  im strukturierten Comparison-Report nebeneinanderstellt.
- Ziel ist ein **technischer Nachweis in Tests**, **kein** echter Backtestbericht.

### Verifizierte Bausteine (bindend für Phase 2)

- `render_comparison_markdown(comparison)` / `normalize_comparison(comparison)`
  existieren und sind rein/deterministisch (kein I/O).
- `build_stair_breakout_for_cooldown()` liefert **18 Bars** (12 flach + Treppe
  101…106), **alle am selben UTC-Tag** (Default-Start `2026-01-01`, 5-Min-Raster,
  `half_spread=0.5`).
- **Verifizierte Signalzahlen** auf diesem Dataset mit
  `MidBreakoutStrategyV1(lookback_bars=12, stop_distance_pct=0.01,
  breakout_threshold_pct=0.0, cooldown_bars=0, max_signals_per_day=…)`:
  - `None` → **5** Signale,
  - `1` → **1**,
  - `2` → **2**.

  > **Wichtig:** `cooldown_bars=0` ist erforderlich, damit **nur** das Tageslimit
  > (nicht zusätzlich der Cooldown) die Signalzahl beeinflusst — saubere
  > Isolation.

## 2. Ziel

Ein Test-/Dokumentationsvergleich auf synthetischem Dataset mit mindestens drei
Varianten:

1. `v1_no_daily_limit` — `max_signals_per_day=None`,
2. `v1_daily_limit_1` — `max_signals_per_day=1`,
3. `v1_daily_limit_2` — `max_signals_per_day=2`.

Optional zusätzlich: `v0` als Referenz ohne Tageslimit (siehe §10.1).

Der strukturierte Vergleich wird über das bestehende `render_comparison_markdown`
erzeugt. **Nur String-Ausgabe im Test; keine Report-Datei; keine Artefakte.**

## 3. Nicht-Ziele

- keine Echtdaten, keine echten Reports, keine Dateien unter `reports/`,
- kein Download, keine API-/Exchange-Anbindung,
- kein Paper-Trading, kein Live-Trading,
- keine Profitabilitätsbewertung, keine Trading-Empfehlung,
- keine Optimierung, keine Parameter-Suche,
- kein Ranking, kein „besser/schlechter", kein „winner",
- keine Änderung an Runner/RiskEngine/CostModel/Strategien/CLI.

## 4. Synthetisches Dataset

Kontrolliertes Dataset mit mehreren Breakout-Signalen am selben UTC-Tag.

> **Empfehlung: bestehenden Builder `build_stair_breakout_for_cooldown()`
> nutzen** — er erfüllt alle Anforderungen (kein neuer Builder nötig, §10.3).

Anforderungen (alle vom `stair`-Builder erfüllt):
- UTC-aware Timestamps, alle Signale am selben UTC-Tag,
- ausreichend Historie für `lookback_bars=12` (12 flache Bars voran),
- mehrere echte Breakouts (Treppe), die ohne Tageslimit mehrere Signale erzeugen,
- keine Zufallswerte, deterministische `bid`/`ask`, keine Echtdaten.

Technische Erwartungen (verifiziert, deterministisch):
- `max_signals_per_day=None` → **5** Signale,
- `max_signals_per_day=1` → **1** (≤ 1),
- `max_signals_per_day=2` → **2** (≤ 2),
- damit: `None > limit_1`, `limit_1 ≤ 1`, `limit_2 ≤ 2`, `limit_2 ≥ limit_1`.

> Nicht interpretieren, nur zählen.

## 5. Vergleichsdatenstruktur

Dict für `normalize_comparison` / `render_comparison_markdown`:

```python
comparison = {
    "title": "Synthetic max_signals_per_day comparison",
    "dataset": {
        "name": "stair_breakout_for_cooldown",
        "type": "synthetic",
        "bars": 18,
        "description": "Multiple same-day breakout opportunities for daily signal limit testing.",
    },
    "variants": [
        {
            "label": "v1_no_daily_limit",
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
                    "max_signals_per_day": None,
                },
            },
            "cost_model": {"fee_rate": 0.0, "spread": 0.0, "slippage": 0.0},
            "technical_results": {
                "signals_total": 5,
                "trades_total": 5,
                "approved_signals": 5,
                "rejected_signals": 0,
            },
        },
        # v1_daily_limit_1: max_signals_per_day=1, signals_total=1, …
        # v1_daily_limit_2: max_signals_per_day=2, signals_total=2, …
    ],
    "notes": [
        "Synthetic data only.",
        "No profitability assessment.",
        "No trading recommendation.",
        "Daily signal limit is a technical signal-density guard.",
    ],
}
```

Regeln:
- `technical_results` enthält **nur** technische Zählwerte
  (`signals_total`, `trades_total`, `approved_signals`, `rejected_signals`).
- **Kein `ending_equity`** (und kein anderes Ergebnis-/Bewertungsfeld).
- Die `technical_results` werden **aus echten Läufen abgeleitet** (siehe §6/§10.2),
  nicht hartkodiert — die obigen Zahlen sind die verifizierten Erwartungen.

## 6. Umsetzungsempfehlung Phase 2

> **Empfehlung: reine Tests, kein neues `src`-Modul.**

Neue Testdatei: `tests/test_max_signals_comparison_report.py`.

Begründung: `render_comparison_markdown` und die Dataset-Builder existieren
bereits; Ziel ist Nachweis/Regression, kein Produktivfeature; keine CLI, keine
Report-Datei.

Der Test soll:
1. synthetisches Dataset bauen (`build_stair_breakout_for_cooldown()`),
2. die drei v1-Varianten (`None`/`1`/`2`) instanziieren,
3. Signale je Variante **zählen** (`generate_signals`),
4. die vier `technical_results` ableiten — entweder per `BacktestRunner` +
   `RiskEngine` (über `InMemoryMarketDataSource`) für den vollen Vierersatz,
   **oder** generate_signals-only für `signals_total` (siehe §10.2),
5. das Vergleichs-Dict bauen,
6. `render_comparison_markdown(comparison)` aufrufen (nur String),
7. den Markdown-Inhalt prüfen.

## 7. Teststrategie Phase 2

1. Report enthält den Titel „Synthetic max_signals_per_day comparison".
2. Report enthält Dataset (`type synthetic`, `name stair_breakout_for_cooldown`).
3. Report enthält die Varianten `v1_no_daily_limit`, `v1_daily_limit_1`,
   `v1_daily_limit_2`.
4. Report enthält die `max_signals_per_day`-Werte `None`, `1`, `2`.
5. Technische Signalzahlen erfüllen: `no_limit > limit_1`, `limit_1 ≤ 1`,
   `limit_2 ≤ 2`, `limit_2 ≥ limit_1` (konkret 5 / 1 / 2).
6. Report enthält die Pflicht-Notes („Synthetic data only.",
   „No profitability assessment.", „No trading recommendation.").
7. Report enthält die Zusatz-Note
   „Daily signal limit is a technical signal-density guard.".
8. Report enthält **kein** `ending_equity`, `winner`, `better`, `worse`,
   `recommendation`.
9. Ausgabe deterministisch (gleicher Vergleich → gleicher Markdown-String).
10. Keine Report-Datei wird geschrieben (reine String-Assertions).
11. Bestehende Tests bleiben grün.

## 8. Doku/README

- `docs/lq-016-max-signals-synthetic-comparison-report.md` um „Phase 2
  Implementation Status" ergänzen.
- README **nur** ändern, falls der Teststand genannt ist (dann nach finalem
  pytest aktualisieren). **Keine** Beispiel-Ergebnisinterpretation in README.

## 9. Kompatibilität

- Kein `src`-Code nötig; keine CLI-/Strategie-/Runner-/RiskEngine-Änderung.
- Tests nutzen ausschließlich vorhandene APIs
  (`render_comparison_markdown`, Builder, ggf. `BacktestRunner`/`RiskEngine`).
- Keine Report-Dateien, keine Echtdaten.

## 10. Offene Entscheidungspunkte

1. **`v0` im Vergleich?**
   → *Empfehlung: optional nein* — Fokus auf das v1-Tageslimit.
2. **`BacktestRunner` oder nur `generate_signals`?**
   → *Empfehlung: nur `generate_signals` für `signals_total`* (max_signals_per_day
   ist eine Strategie-Signaldichte-Regel). Werden alle vier `technical_results`
   konsistent gewünscht, ist ein `BacktestRunner`-Pass über
   `InMemoryMarketDataSource` + `percent_risk` ohne Mehraufwand möglich (auf
   diesem Dataset gilt `approved = signals`, `rejected = 0`, `trades = signals`).
   Bei generate_signals-only werden `trades_total/approved/rejected` aus demselben
   Lauf gespiegelt (oder bleiben über die Normalisierung 0) — in Phase 2
   festlegen.
3. **Neuer Builder nötig?**
   → *Empfehlung: nein* — `build_stair_breakout_for_cooldown()` reicht
   (verifiziert: 18 Bars, gleicher UTC-Tag, 5 Breakouts ohne Limit).
4. **Vergleichsreport später per CLI?**
   → *Empfehlung: später, nicht LQ-016.*

---

## Phase 2 Implementation Status

Umgesetzt (reine Tests, kein neues `src`-Modul):

- **`tests/test_max_signals_comparison_report.py`** implementiert (12 Tests).
- Nutzt **`build_stair_breakout_for_cooldown()`** (18 Bars, gleicher UTC-Tag).
- Nutzt **`MidBreakoutStrategyV1.generate_signals()`** — kein `BacktestRunner`
  nötig; `technical_results.signals_total` aus echter Zählung, die übrigen
  technischen Felder bleiben `0` (reine Signaldichte-Betrachtung).
- Nutzt **`render_comparison_markdown()`** (+ `normalize_comparison`) — nur
  String, **keine** Datei.
- **Varianten** `None` / `1` / `2` getestet; **Signalzahlen 5 / 1 / 2**
  verifiziert (zur Laufzeit geprüft, nicht hartkodiert).
- **Relationen** geprüft: `no_limit(5) > limit_1(1)`, `limit_1 == 1`,
  `limit_2 == 2`, `limit_2 >= limit_1`.
- **Pflicht-Notes** + Zusatz-Note „Daily signal limit is a technical
  signal-density guard." geprüft; **keine** Bewertungs-/Profitabilitätsbegriffe
  (`ending_equity`/`winner`/`better`/`worse`/`recommended`/`profitable`/
  `performance`) — der Disclaimer „No trading recommendation." wird **nicht**
  fälschlich blockiert.
- **Determinismus** geprüft; statischer Pfad-Scan (fragmentbasiert).
- Keine Report-Datei, keine Echtdaten, keine Profitabilitätsbewertung.
- **pytest: 345 passed** (lokale `.venv`).

`src/`, CLI, Runner, RiskEngine, Strategien unverändert. Kein Push.

---

*Research-/Backtesting-Kontext. Keine Live-/Paper-Trading-Funktion, keine
Exchange-Anbindung, keine Profitabilitätsaussage, keine Handelsempfehlung.*
