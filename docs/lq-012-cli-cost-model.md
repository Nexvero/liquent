# LQ-012 — CLI Cost Model Parameters

> Status: **Phase 1 — Spezifikation / Dokumentation.** Keine Implementierung,
> keine Code-Änderung in `src/`. Dieses Dokument plant, wie das bestehende
> `CostModel` künftig über die CLI parametrisierbar und im Report ausweisbar
> wird.

## 1. Ausgangslage

- Der `BacktestRunner` nutzt ein `CostModel` (`src/liquent/backtesting/runner.py`)
  und wendet Kosten über `calculate_trade_costs`
  (`src/liquent/backtesting/metrics.py`) an — **pro Trade-Leg** (Entry **und**
  Exit werden getrennt belastet, `runner.py` ruft `calculate_trade_costs` zweimal
  auf).
- Die CLI (`src/liquent/cli/backtest_mid_breakout.py`) instanziiert das
  Kostenmodell aktuell **fest** mit `CostModel(fee_rate=0.0, spread=0.0,
  slippage=0.0)` — also frictionless. Es gibt **keine** CLI-Flags dafür.
- Nach LQ-009 (Strategieauswahl) und LQ-011 (`strategy_metadata` im Report) ist
  der nächste technische Schritt, auch **Kostenparameter** explizit über die CLI
  steuerbar und reportbar zu machen.
- Ziel ist **Transparenz und Reproduzierbarkeit**, **keine** Bewertung.

### Verifizierte tatsächliche `CostModel`-Felder (WICHTIG)

`CostModel` ist eine frozen dataclass mit genau diesen Feldern und Semantiken
(verifiziert in `runner.py` + `metrics.py`):

| Feld | Typ / Default | Bedeutung (rein technisch) | Kostenformel je Leg |
|---|---|---|---|
| `fee_rate` | `float = 0.0` | Anteil des Notional (`0.001` = 0,1 %) | `notional * fee_rate` |
| `spread` | `float = 0.0` | **absoluter** Preisaufschlag **pro Einheit** | `abs(quantity) * spread` |
| `slippage` | `float = 0.0` | Anteil des Notional (`0.0005` = 0,05 %) | `notional * slippage` |

mit `notional = price * abs(quantity)`; `total_cost = fee_cost + spread_cost +
slippage_cost`. Es gibt **keine** `*_bps`-Felder.

> **Abweichung von der ursprünglichen Aufgabenskizze:** Die Skizze nannte
> beispielhaft `--spread-bps` / `--slippage-bps`. Der **reale** Code kennt diese
> nicht — `spread` ist ein **absoluter** Preisaufschlag pro Einheit (keine
> Basispunkte) und `slippage` ein Notional-Anteil. Diese Spezifikation verwendet
> daher die **tatsächlichen** Feldnamen (`--fee-rate`, `--spread`, `--slippage`).
> Eine bps-Variante würde eine nicht vorhandene Umrechnungsschicht erfordern und
> ist hier nur als optionaler Entscheidungspunkt (siehe §10) vermerkt.

### Bereits vorhandene Report-Sichtbarkeit

Der Runner schreibt `fee_rate`, `spread`, `slippage` (und `frictionless`) bereits
**skalar** in `result.parameters`. Diese erscheinen damit **schon heute** im
Markdown-Abschnitt „## Parameters". LQ-012 ergänzt CLI-Steuerung und — optional —
eine **gruppierte** Cost-Model-Darstellung (siehe §6/§10).

## 2. Ziel

Die CLI soll Parameter für die realen `CostModel`-Felder erhalten:

```text
--fee-rate  FLOAT     (Anteil des Notional; 0.001 = 0,1 %)
--spread    FLOAT     (absoluter Preisaufschlag pro Einheit)
--slippage  FLOAT     (Anteil des Notional; 0.0005 = 0,05 %)
```

Ziel:
- Kostenmodell **explizit steuerbar** machen,
- effektive Kostenparameter im Report **ausweisen**,
- Default bleibt **rückwärtskompatibel** (frictionless wie bisher),
- **keine** Interpretation der Ergebnisse.

## 3. Default-Verhalten

- Default entspricht exakt dem bisherigen CLI-Verhalten:
  `fee_rate = 0.0`, `spread = 0.0`, `slippage = 0.0` (frictionless).
- Bestehende CLI-Läufe ohne die neuen Flags bleiben **byte-identisch**
  reproduzierbar (der `frictionless`-Parameter bleibt `True`, die bestehenden
  `fee_rate/spread/slippage`-Zeilen im Report bleiben `0.0`).

## 4. CLI-Parameter

Geplante Flags (Namen = reale `CostModel`-Felder):

| Flag | Ziel-Feld | Default | Bedeutung (technisch) |
|---|---|---|---|
| `--fee-rate FLOAT` | `fee_rate` | `0.0` | Notional-Anteil; `0.001` = 0,1 % je Leg |
| `--spread FLOAT` | `spread` | `0.0` | absoluter Aufschlag pro Einheit (`abs(qty) * spread`) |
| `--slippage FLOAT` | `slippage` | `0.0` | Notional-Anteil; `0.0005` = 0,05 % je Leg |

Hinweis (rein technisch, keine Markteinschätzung): Kosten fallen je **Leg**
(Entry und Exit) separat an; ein Trade trägt damit Entry- **und** Exit-Kosten.

## 5. Validierung

CLI-seitige Frühvalidierung (analog zu den bestehenden `_validate_ranges`):

- `fee_rate >= 0.0`
- `spread >= 0.0`
- `slippage >= 0.0`

Begründung: `CostModel`/`calculate_trade_costs` enthalten **keine** eigene
Negativ-Prüfung (frozen dataclass mit float-Defaults). Die CLI validiert daher
früh mit klarer Meldung (Usage-Exit), bevor gerechnet wird. **`CostModel` und der
Runner werden NICHT geändert.**

Keine Obergrenze (Code/Tests legen keine nahe). Eine optionale Obergrenze ist nur
als offener Entscheidungspunkt vermerkt (§10).

## 6. Report-Integration

Analog zu LQ-011 `strategy_metadata`: ein **eigenes, optionales** Summary-Feld
`cost_metadata` (additiv, backward-compatible), **nicht** verschachtelt in
`result.parameters` (dort nur Skalare). Markdown-Abschnitt (nur bei vorhandenen
Metadaten), z. B. nach „## Strategy" bzw. „## Experiment":

```markdown
## Cost Model

| Parameter | Value |
| --------- | ----- |
| fee_rate  | 0.0   |
| spread    | 0.0   |
| slippage  | 0.0   |
```

`summary_to_dict` ergänzt analog einen Schlüssel `"cost_model"` **nur** bei
vorhandener `cost_metadata`.

> **Redundanz-Hinweis (verifiziert):** `fee_rate/spread/slippage` stehen bereits
> in „## Parameters". Ein eigener „## Cost Model"-Abschnitt ist daher eine
> **gruppierte, explizite** Zweitdarstellung. Das ist gewollt (Symmetrie zu
> `strategy_metadata`, klare Auffindbarkeit), aber als Entscheidungspunkt (§10)
> dokumentiert. Bestehende „## Parameters"-Zeilen bleiben unverändert.

## 7. CLI-Integration (Plan für Phase 2)

Nach Parse/Validierung (Werte sind reale, nicht-Sentinel-Floats):

```python
cost_model = CostModel(
    fee_rate=args.fee_rate,
    spread=args.spread,
    slippage=args.slippage,
)

cost_metadata = {
    "fee_rate": args.fee_rate,
    "spread": args.spread,
    "slippage": args.slippage,
}
```

Report-Aufruf künftig (additiver, keyword-only Parameter — analog
`strategy_metadata`):

```python
summary = summarize_backtest_result(
    result,
    title="Liquent MidBreakout Backtest",
    strategy_metadata=strategy_metadata,
    cost_metadata=cost_metadata,
)
```

Die bestehende Zeile
`cost_model=CostModel(fee_rate=0.0, spread=0.0, slippage=0.0)` im `BacktestRunner`
-Aufruf wird durch das aus den CLI-Argumenten gebaute `cost_model` ersetzt
(Defaults `0.0` → unverändertes Verhalten ohne Flags).

## 8. Tests für Phase 2

1. CLI ohne Kostenparameter bleibt rückwärtskompatibel (frictionless).
2. Default-`CostModel` entspricht bisherigem Verhalten (`frictionless=True`).
3. `--fee-rate` wird akzeptiert und ans `CostModel` übergeben.
4. `--spread` wird akzeptiert und ans `CostModel` übergeben.
5. `--slippage` wird akzeptiert und ans `CostModel` übergeben.
6. negative `--fee-rate` wird abgelehnt (Usage-Exit, keine Datei).
7. negative `--spread` wird abgelehnt.
8. negative `--slippage` wird abgelehnt.
9. Report enthält „## Cost Model" bei vorhandener `cost_metadata`.
10. Report ohne `cost_metadata` bleibt backward-compatible (kein Abschnitt).
11. `strategy_metadata` und `cost_metadata` funktionieren gemeinsam.
12. Bestehende Tests bleiben grün (insb. `test_backtesting.py`-Kostentests).
13. Keine Reports committed (Tests nutzen `tmp_path`).
14. Keine Netzwerk-/Live-/Paper-Trading-Pfade (statischer Scan).

## 9. Nicht-Ziele

- keine Profitabilitätsbewertung,
- keine Trading-Empfehlung,
- keine Optimierung, keine Parameter-Suche,
- keine Echtdatenläufe,
- keine Reports committen,
- keine Änderung an Strategien,
- keine Änderung an RiskEngine,
- **keine Änderung an `CostModel`/Runner/`calculate_trade_costs`**,
- keine Exchange-API, kein Paper-Trading, kein Live-Trading.

## 10. Offene Entscheidungspunkte

1. **`cost_metadata` immer im Report oder nur bei gesetzten Flags?**
   → *Empfehlung: immer, sobald die CLI einen Report erzeugt* — damit auch
   0-Kosten explizit dokumentiert sind (Reproduzierbarkeit). Technisch: die CLI
   übergibt `cost_metadata` stets (Defaults `0.0`).
2. **`cost_metadata` als eigenes Summary-Feld (analog `strategy_metadata`)?**
   → *Empfehlung: ja* (Symmetrie, additiv, backward-compatible).
3. **Obergrenze für `fee_rate`/`spread`/`slippage`?**
   → *Empfehlung: zunächst nein; nur `>= 0` validieren.*
4. **README in Phase 2 anpassen?**
   → *Empfehlung: ja*, sobald die CLI-Flags implementiert sind (CLI-Abschnitt +
   Teststand aktualisieren).
5. **(Verifiziert) Feldnamen `--spread`/`--slippage` vs. `--*-bps`?**
   → *Empfehlung: reale Feldnamen verwenden* (`--spread` absolut, `--slippage`
   Notional-Anteil). Eine bps-Convenience-Schicht ist optional und würde eine
   Umrechnung erfordern — nicht Teil von Phase 2.
6. **(Verifiziert) Redundanz zu „## Parameters":**
   → Kostenfelder stehen dort bereits; der „## Cost Model"-Abschnitt ist eine
   bewusste gruppierte Zweitdarstellung. Entscheidung in Phase 2 bestätigen.

---

## Phase 2 Implementation Status

Umgesetzt (additiv, backward-compatible):

- **CLI-Flags implementiert:** `--fee-rate`, `--spread`, `--slippage`
  (`backtest_mid_breakout.py`), reale `CostModel`-Felder (keine `*_bps`).
- **Defaults `0.0` / `0.0` / `0.0`** → frictionless, byte-identisch zum
  bisherigen Verhalten ohne die Flags (`frictionless=True` bleibt).
- **Negative Werte** werden CLI-seitig früh abgelehnt (`_validate_ranges`,
  Usage-Exit, keine Report-Datei).
- **`CostModel` wird aus CLI-Werten gebaut** — die zuvor feste frictionless-
  Instanziierung ist ersetzt. `CostModel`/Runner/`calculate_trade_costs`
  **unverändert**.
- **`cost_metadata` an Reporting übergeben:** `summarize_backtest_result(…, *,
  strategy_metadata=None, cost_metadata=None)` — neues additives, keyword-only
  Feld; separates Summary-Feld `BacktestExperimentSummary.cost_metadata`
  (Default `None`), normalisiert auf `fee_rate, spread, slippage`.
- **Markdown-Report:** Abschnitt `## Cost Model` (nur bei vorhandener
  `cost_metadata`) — nach `## Strategy` (falls vorhanden), vor `## Metrics`. Die
  CLI übergibt `cost_metadata` **immer**, sodass auch 0-Kosten explizit
  dokumentiert sind.
- **`summary_to_dict`** ergänzt den Schlüssel `"cost_model"` **nur** bei
  vorhandener `cost_metadata`.
- **`BacktestResult.parameters` bleibt skalar** (runner.py unverändert); die
  bestehenden `fee_rate/spread/slippage`-Zeilen in `## Parameters` bleiben — der
  `## Cost Model`-Abschnitt ist die bewusste gruppierte Zweitdarstellung.
- **Terminal-Hinweis** ergänzt:
  `cost_model: fee_rate=… spread=… slippage=…`.
- **Tests:** `tests/test_cli_cost_model.py` (10) + `tests/test_reporting_cost_metadata.py` (7).
  Bestehende Tests bleiben grün.
- **pytest: 295 passed** (lokale `.venv`).

Runner/RiskEngine/CostModel/v0-/v1-Strategie unverändert. Kein Push.

Keine Profitabilitätsaussage, keine Echtdatenbewertung.

---

*Research-/Backtesting-Kontext. Keine Live-/Paper-Trading-Funktion, keine
Exchange-Anbindung, keine Profitabilitätsaussage, keine Handelsempfehlung.*
