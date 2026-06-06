# Liquent — Technical Status and Roadmap

> Konsolidierte, rein **technische** Status- und Roadmap-Übersicht (LQ-017
> Phase 1). Keine Implementierung, keine Echtdaten, **keine
> Profitabilitätsbewertung**, keine Trading-Empfehlung.

## 1. Aktueller Stand (verifiziert)

- **Letzter Commit:** `79392af` — *Add max signals comparison report test*
  (auf `origin/main`).
- **Teststand:** **345 passed** (lokale `.venv`, `python -m pytest`).
- **Branch:** `main` synchron mit `origin/main` (kein ahead/behind).
- **Working Tree:** clean.
- **Doku-Inventar:** `docs/lq-009 … lq-016` (8 LQ-Specs) + diese Datei.

## 2. Abgeschlossene Foundations / Schritte

| ID | Thema | Kurzbeschreibung (technisch) |
|---|---|---|
| LQ-003 | Data Foundation | `HistoricalFileSource`, OHLCV-Validierung, Gap-/History-Reports |
| LQ-004 | Risk Foundation | `RiskEngine`, `percent_risk`-Sizing (Pflicht-`stop_price`, fail-safe) |
| LQ-005 | Backtesting Foundation | `BacktestRunner` (Close-to-Close, deterministisch), Metrics, Reporting |
| LQ-006 | MidBreakoutStrategy v0 | erste regelbasierte Mid-/Close-Breakout-Strategie |
| LQ-007 | CLI + Echtdatenlauf | lokales CLI; `--gap-policy`/`--max-gaps`; manueller 30-Tage-CSV-Lauf |
| LQ-008 | MidBreakoutStrategyV1 | additive v1 (Breakout-Threshold, Cooldown), v0 als Regressionsbasis |
| LQ-009 | CLI Strategy Selection | `--strategy v0\|v1`, v1-only-Gating, Sentinel-Defaults |
| LQ-010 | Synthetic Strategy Comparison | deterministische v0/v1-Vergleichstests |
| LQ-011 | Strategy Metadata Reporting | additives `strategy_metadata` in Report/Dict |
| LQ-012 | CLI Cost Model Parameters | `--fee-rate`/`--spread`/`--slippage`; `cost_metadata` |
| LQ-013 | Structured Synthetic Comparison Reporting | `comparison_reporting.py` (Markdown-Vergleich) |
| LQ-014 | Synthetic Dataset Builders | `tests/helpers/synthetic_data.py` (Builder, In-Memory-Source) |
| LQ-015 | max_signals_per_day | aktives UTC-Tageslimit in v1 + CLI-Flag |
| LQ-016 | Synthetic Comparison Report (max_signals_per_day) | kontrollierter Vergleichstest (None/1/2 → 5/1/2) |

*Keine Profitabilitätsbewertung — die Tabelle beschreibt ausschließlich
technischen Funktionsumfang.*

## 3. Strategie-Stand

### MidBreakoutStrategy v0 (`src/liquent/strategy/mid_breakout.py`)

- **Regressionsbasis, unverändert.**
- Default `lookback_bars=3`; **kein** Threshold, **kein** Cooldown, **kein**
  `max_signals_per_day`.
- Strikter Breakout (`mid > max(window)` / `< min(window)`), `strength` fix `1.0`.

### MidBreakoutStrategyV1 (`src/liquent/strategy/mid_breakout_v1.py`)

Parameter (Defaults):
- `lookback_bars=12`
- `stop_distance_pct=0.01`
- `breakout_threshold_pct=0.001`
- `cooldown_bars=3`
- `allow_short=True`
- `min_strength=0.0`
- `max_signals_per_day=None`

Technische Gates / Eigenschaften:
- **Breakout-Threshold:** LONG `mid > prev_high·(1+thr)`, SHORT
  `mid < prev_low·(1-thr)`; `thr=0.0` reproduziert v0.
- **Cooldown:** nach erzeugtem Signal `cooldown_bars` Bars überspringen.
- **Tageslimit `max_signals_per_day`:** optional, je UTC-Tag
  (`timestamp.date()`); `None` = deaktiviert; letztes Gate vor dem Append; ein
  dadurch verworfenes Signal löst **keinen** Cooldown aus.
- **Kein Signal auf dem letzten Bar** (Close-to-Close braucht Folge-Bar).
- **Stop-Logik:** `mid·(1∓stop_distance_pct)` (percent_risk-konform).
- **`strength`/`min_strength`:** reiner Signalfilter; RiskEngine skaliert
  **nicht** über `strength`.
- **Keine Positionslogik;** **kein** echter Stop-Exit im Runner
  (`stop_price` dient nur dem Sizing — Exit ist stets der Folge-Bar-Mid).

## 4. CLI-Stand (`src/liquent/cli/backtest_mid_breakout.py`)

- `--strategy v0|v1` (Default **v0**, byte-identisch reproduzierbar).
- **v1-only-Gating** (bei v0 hart abgelehnt): `--breakout-threshold-pct`,
  `--cooldown-bars`, `--max-signals-per-day`.
- Gemeinsam: `--lookback-bars`, `--stop-distance-pct`, `--min-strength`,
  `--allow-short`.
- **Kostenmodell CLI-parametrisierbar:** `--fee-rate`, `--spread`, `--slippage`
  (Default `0.0` = frictionless).
- **Strategy- und Cost-Metadata** werden in den Markdown-Report geschrieben
  (`## Strategy`, `## Strategy Parameters`, `## Cost Model`).
- **Keine** Live-/Paper-/Exchange-/Netzwerk-/Download-Pfade (statisch getestet);
  fixer `sizing_mode="percent_risk"`; deterministischer Output.

## 5. Reporting-Stand

**Einzelreport (`src/liquent/backtesting/reporting.py`):**
- additives, optionales `strategy_metadata` (family/key/name/params),
- additives, optionales `cost_metadata` (fee_rate/spread/slippage),
- `BacktestResult.parameters` bleibt **skalar** (`str|int|float|bool`) — Metadaten
  liegen in separaten, optionalen Summary-Feldern (Default `None` →
  byte-identisch).

**Comparison-Reporting (`src/liquent/backtesting/comparison_reporting.py`):**
- `normalize_comparison` (stabile Defaults/Feldreihenfolge),
  `render_comparison_markdown` (**nur String, kein I/O**),
- technische Vergleichstabellen (Signals/Trades/Approved/Rejected je Variante),
- **keine** Bewertungssprache (kein Ranking/winner/better/worse),
- **kein** `ending_equity` im Comparison-Report.

## 6. Test-/Synthetic-Stand

- `tests/helpers/synthetic_data.py`:
  - `SyntheticDataset` (frozen), `make_mid_series_dataset` (deterministische
    UTC-Stamps, `bid=mid∓half_spread`, Validierung),
  - `InMemoryMarketDataSource` (`market_data()` + `order_book_snapshots()`),
  - Builder: `build_sideways_with_micro_long_breakout`,
    `build_sideways_with_micro_short_breakout`,
    `build_stair_breakout_for_cooldown`.
- Synthetische Tests decken ab: v0/v1-Vergleich, Threshold, Cooldown,
  `max_signals_per_day` (Strategie + CLI + Comparison-Report), Strategy-/Cost-
  Metadata-Reporting, CostModel-CLI, CLI-Gating, Comparison-Rendering.
- **Importweg:** `pyproject.toml` `pytest.pythonpath = ["src", "tests"]`
  (Helfer als `helpers.*`).

## 7. Sicherheits- und Projektgrenzen (bindend)

- keine Echtdaten in Tests/Commits; keine Reports committen
  (`reports/*` git-ignoriert außer `reports/README.md`; `data/raw|processed`
  ignoriert),
- keine API-Keys/Zugangsdaten, keine Netzwerk-Calls, kein Download,
- keine Exchange-Anbindung, kein Paper-Trading, kein Live-Trading,
- keine Profitabilitätsbewertung, keine Trading-Empfehlung,
- keine Optimierung/Parameter-Suche ohne separate Spezifikation.

## 8. Offene technische Themen (priorisiert)

### LQ-018 — CLI Help/Examples Review
CLI-Hilfe, README-Beispiele und Parametererklärungen konsolidieren. **Keine** neue
Logik — reiner Doku-/UX-Schritt.

### LQ-019 — JSON/Structured Output Spezifikation
Prüfen, ob Reports neben Markdown optional JSON/Dict liefern sollen
(`summary_to_dict`/`normalize_comparison` sind bereits JSON-fähig). **Keine**
Report-Artefakte committen.

### LQ-020 — Runner Stop-Exit Spezifikation
Aktuell nutzt der Runner `stop_price` nur fürs Sizing; Exit ist Folge-Bar-Mid.
Separat spezifizieren, ob ein **echter** Stop-Exit modelliert werden soll
(Runner-Änderung, nicht Strategie).

### LQ-021 — Position State / Holding Period Spezifikation
Aktuell 1-Bar-Haltedauer (Close-to-Close). Positionszustand/variable Haltedauer
wäre eine **Runner**-Änderung, keine Strategieänderung.

### LQ-022 — Cost Model Validation Erweiterung
Optional Obergrenzen/Warnungen für `fee_rate`/`spread`/`slippage`. **Keine**
Marktannahmen, nur technische Plausibilitätsgrenzen.

### LQ-023 — Controlled Real-Data Re-Run Plan
Nur **Planung**, keine Ausführung. Echtdatenlauf ausschließlich nach expliziter
Freigabe, manuell bereitgestellt. **Keine** Profitabilitätsbewertung.

## 9. Empfohlene nächste Phase

> **Empfehlung: LQ-018 — CLI Help/Examples Review.**
>
> Begründung: Die CLI ist inzwischen deutlich gewachsen
> (`--strategy`, v1-only-Parameter, Kostenmodell). Vor neuen
> Backtesting-Mechaniken sollten CLI-Hilfe, README und Beispiele konsistent sein.
> Reiner Doku-/UX-Schritt — kein Risiko für Strategie/Runner/RiskEngine.

## 10. Nicht-Ziele dieser Konsolidierung

- keine Implementierung, keine Strategieänderung, keine CLI-Änderung,
- keine Runner-/RiskEngine-Änderung, keine Tests ändern,
- keine Echtdaten, keine Reports,
- kein Commit ohne Freigabe, kein Push.

## 11. Visual Preview

- Visual Preview docs index: `docs/visual-preview-index.md`
- Quickstart: `docs/lq-025-visual-preview-quickstart.md`
- Stabilization checkpoint: `docs/lq-027-visual-preview-stabilization-checkpoint.md`
- Controlled Streamlit smoke-test checklist: `docs/lq-028-controlled-streamlit-smoke-test-checklist.md`
- Review pause / next-track decision: `docs/lq-029-visual-preview-review-pause-next-track.md`
- Manual Streamlit smoke-test execution plan: `docs/lq-030-manual-streamlit-smoke-test-execution-plan.md`
- Status: local visual preview checkpoint documented;
  LQ-028 documents the manual smoke-test procedure (no automation, no deployment);
  Visual Preview reached a stable local checkpoint; next track should be chosen explicitly;
  next step is manual UI smoke-test execution, not new feature work;
  no live/paper/exchange/API functionality.

---

*Research-/Backtesting-Kontext. Keine Live-/Paper-Trading-Funktion, keine
Exchange-Anbindung, keine Profitabilitätsaussage, keine Handelsempfehlung.*
