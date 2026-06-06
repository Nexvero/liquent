# LQ-010 — Synthetischer v0/v1-Vergleich

> Status: **Phase 1 umgesetzt** als Test
> `tests/test_synthetic_strategy_comparison.py`. Kein Report-Artefakt, keine
> Echtdaten, kein Commit ohne Freigabe.

## Zweck

Ein kontrollierter, rein **technischer** Vergleich zwischen
`MidBreakoutStrategy` (v0) und `MidBreakoutStrategyV1` (v1). Ziel ist
ausschließlich, das **Verhalten** der beiden Strategien auf identischen Daten
sichtbar und reproduzierbar zu machen — **keine** Aussage über Profitabilität,
Qualität oder Eignung.

## Datensatz

- **Vollständig synthetisch und deterministisch** (im Test als Mid-Serien
  konstruiert; `bid = ask = mid`).
- **Keine Echtdaten**, keine BTC-/Exchange-Daten, keine Dateien unter
  `data/raw/`, kein Download, keine API, keine Netzwerk-Calls.
- Zeitstempel deterministisch (feste UTC-Minuten), kein Zufall.
- 12 flache Bars Historie je Serie, damit `lookback_bars = 12` erfüllt ist.

Serien:

| Serie | Muster | Zweck |
|---|---|---|
| `_MICRO_LONG` | 12× 100, dann 100.05 / 100 / 100 / 102 / 100 | Mikro-Ausbruch (+0,05 %) vs. echter Long-Breakout (+2 %) |
| `_MICRO_SHORT`| 12× 100, dann 99.95 / 100 / 100 / 98 / 100 | Mikro-Short vs. echter Short-Breakout |
| `_STAIR` | 12× 100, dann 101…106 | jeder Bar ein echter Breakout → Cooldown-Wirkung |

Gemeinsame Parameter: `lookback_bars = 12`, `stop_distance_pct = 0.01`,
v1-`breakout_threshold_pct = 0.001` (0,1 %).

## Getestete technische Erwartungen

1. v0 erzeugt beim Mikro-Ausbruch ein (zusätzliches) Long-Signal.
2. v1 **blockt** den Mikro-Ausbruch über `breakout_threshold_pct`, behält den
   echten Long-Breakout.
3. v1 liefert beim echten Long-Breakout ein Long-Signal mit konsistentem Stop
   (`stop < mid`).
4. v1 liefert beim echten Short-Breakout ein Short-Signal; der Mikro-Short wird
   geblockt (`stop > mid`).
5. v1-Cooldown reduziert Folge-Signale (Treppe: `cooldown_bars=0` → 5,
   `cooldown_bars=3` → 2).
6. Beide Strategien laufen durch dieselbe Backtest-/Risk-Strecke
   (`BacktestRunner` + `RiskEngine` im `percent_risk`-Modus); verglichen werden
   nur technische Kennzahlen: `signals_total`, `approved_signals`,
   `rejected_signals`, `number_of_trades`, `strategy` (Klassenname). Es gilt
   `approved + rejected == signals_total` und `approved == trades`.
7. Determinismus: gleicher synthetischer Input → identische Gate-Zählungen.

Zusätzlich: ohne Threshold/Cooldown (`breakout_threshold_pct=0.0`,
`cooldown_bars=0`) sind v0 und v1 auf der Treppe **deckungsgleich**
(Regressionsanker).

## Ergebnis (technisch, nach `pytest`)

Reine Signal-Ebene (deterministisch verifiziert):

| Serie | v0 | v1 (cd=3) | v1 (cd=0) |
|---|---|---|---|
| `_MICRO_LONG` | 2 (i=12, i=15) | 1 (i=15) | — |
| `_MICRO_SHORT`| 2 (i=12, i=15) | 1 (i=15) | — |
| `_STAIR` | 5 | 2 | 5 |

Runner-/Risk-Strecke auf `_MICRO_LONG`:

| Strategie | signals_total | approved | rejected | trades |
|---|---|---|---|---|
| v0 `MidBreakoutStrategy` | 2 | 2 | 0 | 2 |
| v1 `MidBreakoutStrategyV1` | 1 | 1 | 0 | 1 |

> **Keine Profitabilitätsbewertung.** `ending_equity` ist ein mechanisches
> Backtest-Feld und wird hier **nicht** interpretiert. Die Zahlen beschreiben
> ausschließlich das deterministische Signal-/Gate-Verhalten auf synthetischen
> Daten — kein „besser", „profitabler" oder „empfohlen".

## Beobachtung (rein technisch)

- Der `breakout_threshold_pct`-Filter wirkt wie spezifiziert: Mikro-Ausbrüche
  unterhalb der Schwelle erzeugen in v1 kein Signal, echte Breakouts schon.
- `cooldown_bars` reduziert deterministisch die Folge-Signaldichte.
- Beide Strategien sind über die identische Risk-First-Strecke austauschbar
  (kein Eingriff in Runner/RiskEngine nötig).

---

*Research-/Backtesting-Kontext. Keine Live-/Paper-Trading-Funktion, keine
Exchange-Anbindung, keine Profitabilitätsaussage, keine Handelsempfehlung.*
