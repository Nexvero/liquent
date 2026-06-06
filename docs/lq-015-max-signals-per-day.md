# LQ-015 — max_signals_per_day for MidBreakoutStrategyV1

> Status: **Phase 1 — Spezifikation / Dokumentation.** Keine Implementierung,
> keine Code-Änderung in `src/`, keine Echtdaten. Plant die **aktive** optionale
> Begrenzung der Signale pro UTC-Kalendertag in `MidBreakoutStrategyV1`.

## 1. Ausgangslage

- `MidBreakoutStrategyV1` wurde in **LQ-008** eingeführt.
- `max_signals_per_day` ist **bereits als optionaler Parameter vorhanden** und
  **konstruktor-validiert** (`None` oder `> 0`), wird aber in
  `generate_signals` **bewusst nicht erzwungen** (LQ-008 Phase 2).
- **LQ-009** hat die CLI-Strategieauswahl + v1-only-Gating eingeführt.
- **LQ-010/LQ-014** haben synthetische Tests und wiederverwendbare Dataset-Helfer
  (`tests/helpers/synthetic_data.py`) eingeführt — damit lässt sich das
  Tageslimit deterministisch testen (mehrere Breakouts pro Tag / über zwei Tage).

`max_signals_per_day` ist ein **technischer Signaldichte-Guard**. Keine
Profitabilitätsbewertung, keine Trading-Empfehlung.

### Verifizierter Code-Stand (bindend für Phase 2)

- `src/liquent/strategy/mid_breakout_v1.py`:
  - Konstruktor: `max_signals_per_day: int | None = None`; Validierung
    `if max_signals_per_day is not None and max_signals_per_day <= 0: raise ValueError(...)`
    — **bereits vorhanden**, Phase 2 braucht hier **keine** Änderung.
  - `generate_signals`-Schleife (verifizierte Struktur): Cooldown-Gate
    (`if i < next_allowed: continue`) → Threshold/`allow_short` → Stop →
    `strength`/`min_strength`-Filter → `signals.append(...)` →
    `next_allowed = i + cooldown_bars + 1`.
- **Bestehender Test, der sich ändern MUSS:**
  `tests/test_strategy_v1.py::test_max_signals_per_day_not_enforced_in_phase2`
  prüft aktuell, dass `max_signals_per_day=1` **nicht** greift (4 Signale). Mit
  der Aktivierung wird dieser Test **falsch** und ist in Phase 2 durch einen
  Enforcement-Test zu **ersetzen** (siehe §7/§10). Das ist die **einzige**
  bestehende Verhaltensannahme, die kippt.

## 2. Ziel

Aktive, optionale Begrenzung der Signale **pro UTC-Kalendertag** in
`MidBreakoutStrategyV1`:

- `max_signals_per_day is None` → Verhalten **unverändert** zur bisherigen v1.
- `max_signals_per_day = N` →
  - pro UTC-Kalendertag höchstens `N` Signale,
  - Zählung über `signal.timestamp.date()` (UTC),
  - nach `N` Signalen an einem Tag werden weitere Signale dieses Tages
    übersprungen,
  - am nächsten UTC-Tag beginnt der Zähler neu.

## 3. Nicht-Ziele

- keine Profitabilitätsbewertung, keine Trading-Empfehlung,
- keine Optimierung, keine Parameter-Suche,
- keine Echtdatenläufe,
- keine Änderung an RiskEngine, Runner, Positionslogik,
- keine Live-/Paper-/Exchange-Anbindung, kein Download,
- keine Reports committen.

## 4. Strategie-Regeln (genaue Logik)

In `MidBreakoutStrategyV1`:

- Feld: `max_signals_per_day: int | None = None` (bereits vorhanden).
- Konstruktorvalidierung: `None` erlaubt; sonst `> 0` (bereits vorhanden).

Signal-Loop (Erweiterung, deterministisch):

```text
daily_counts: dict[date, int] = {}     # vor der Schleife initialisieren
für jeden Bar i:
    1) bestehende Gates ZUERST (unverändert):
       - gültiger i-Bereich (lookback_bars <= i <= n-2)
       - Cooldown-Gate (if i < next_allowed: continue)
       - Threshold (long/short) + allow_short
       - stop_price-Berechnung (Fail-safe stop_price > 0)
       - strength / min_strength-Filter
    2) Wenn daraus ein Signal entstehen WÜRDE:
       signal_day    = bars[i].timestamp.date()        # UTC-Datum
       current_count = daily_counts.get(signal_day, 0)
       wenn max_signals_per_day is not None und current_count >= max_signals_per_day:
           - Signal NICHT erzeugen (kein append)
           - daily_counts unverändert
           - next_allowed NICHT setzen  → KEIN Cooldown ausgelöst
           - continue
       sonst:
           - Signal erzeugen (append)
           - daily_counts[signal_day] = current_count + 1
           - next_allowed = i + cooldown_bars + 1   (Cooldown wie bisher)
```

**Invarianten:**
- Cooldown greift **nur nach tatsächlich erzeugtem Signal**.
- Ein durch das Tageslimit verworfenes Signal löst **keinen** Cooldown aus
  (folgende Bars desselben Tages werden regulär weiter geprüft, bis der nächste
  Tag den Zähler zurücksetzt — oder bis ein erzeugtes Signal wieder Cooldown
  setzt).
- Reihenfolge ist wichtig: Das Tageslimit ist das **letzte** Gate vor `append`,
  damit es exakt die *sonst erzeugten* Signale zählt.

## 5. UTC-Tagesgrenze

- `MarketData.timestamp` ist ein `datetime`; die Tests nutzen **UTC-aware**
  Zeitstempel (`tzinfo=timezone.utc`), auch über den LQ-014-Helfer.
- Zählung über `bars[i].timestamp.date()`.
- **Keine** lokale Zeitzone, **keine** Wall-Clock, **keine** Systemzeit, **kein**
  `generated_at`. Vollständig deterministisch.
- **Naive Timestamps:** `date()` wird direkt verwendet (kein automatisches
  Umdeuten naiver Zeitstempel). Tests verwenden ausschließlich UTC-aware Daten,
  sodass `date()` das UTC-Datum ist. (Eine `astimezone(utc)`-Konvertierung wird
  bewusst **nicht** eingeführt, um naive Daten nicht still umzudeuten.)

## 6. CLI-Auswirkung

**Option A — nur Strategie, keine CLI.**
- *Pro:* kleiner Schritt, nur Strategie-Tests, CLI unverändert.
- *Contra:* nicht über CLI setzbar.

**Option B — Strategie + CLI-Flag `--max-signals-per-day INT` (nur `--strategy v1`).**
- *Pro:* direkt nutzbar; `strategy_metadata` kann den Wert tragen.
- *Contra:* mehr Tests; v1-only-Gating + Validierung + Reporting/README erweitern.

> **Empfehlung: Option B**, sauber abgegrenzt:
> - `--max-signals-per-day` **nur** für `strategy=v1`; bei `strategy=v0` (auch
>   Default-v0 ohne `--strategy`) **hart ablehnen** — analog zum bestehenden
>   v1-only-Gating in `_resolve_strategy_args` (Sentinel `None`).
> - Default `None`; Validierung (in `_validate_ranges`, nur bei v1): `> 0`.
> - In `strategy_metadata.params` (v1) **aufnehmen** — auch als `None`, weil es
>   ein echter v1-Parameter ist und die Reproduzierbarkeit erhöht.

CLI-Verdrahtung (Plan): `--max-signals-per-day default=None, type=int`; in
`_resolve_strategy_args` als v1-only behandeln (bei v0 + not None → Usage-Fehler);
an `MidBreakoutStrategyV1(..., max_signals_per_day=args.max_signals_per_day)`
übergeben; v1-`strategy_params` um `"max_signals_per_day": args.max_signals_per_day`
ergänzen.

> **Reporting-Hinweis:** README muss klar dokumentieren: **`None` = deaktiviert**
> (keine aktive Begrenzung). So täuscht der im Report sichtbare `None`-Wert keine
> aktive Funktion vor.

## 7. Tests für Phase 2

**Strategie:**
1. `max_signals_per_day=None` erhält bisheriges Verhalten (Regressionsanker).
2. `max_signals_per_day=1` begrenzt mehrere Signale am selben UTC-Tag auf 1.
3. `max_signals_per_day=2` begrenzt auf 2.
4. Zähler resetet am nächsten UTC-Tag (Dataset über zwei UTC-Tage).
5. Durch Tageslimit verworfenes Signal löst **keinen** Cooldown aus
   (nachfolgendes erlaubtes Signal entsteht, das es ohne Limit-Verwurf-Cooldown
   geben muss).
6. `max_signals_per_day <= 0` wird abgelehnt (bereits vorhanden — beibehalten).
7. Threshold-/Cooldown-Verhalten bleibt unverändert.
8. Determinismus bleibt erhalten.

> **Achtung (verifiziert):** Test
> `test_max_signals_per_day_not_enforced_in_phase2` **ersetzen** (er prüft das
> Gegenteil). Der Valid-Bounds-Test (`max_signals_per_day=1` als gültiger Wert)
> bleibt gültig.

**CLI (Option B):**
9. `--strategy v1 --max-signals-per-day 2` akzeptiert.
10. `--strategy v0 --max-signals-per-day 2` abgelehnt.
11. `--max-signals-per-day` ohne `--strategy v1` abgelehnt (Default v0).
12. `--max-signals-per-day 0` abgelehnt.
13. negative Werte abgelehnt.
14. `strategy_metadata`/Report enthält `max_signals_per_day` (v1).
15. Bestehende CLI-Tests bleiben grün.

**Synthetische Helfer:**
16. Dataset mit mehreren Breakouts am selben UTC-Tag (z. B. die `stair`-Serie,
    1-Minuten-Raster — alle am selben Tag).
17. Dataset mit Breakouts über **zwei** UTC-Tage (Start so wählen, dass die
    Treppe die Mitternachtsgrenze überschreitet, z. B. `start=23:55` bei
    5-Minuten-Raster).
18. Keine Echtdaten.
19. Keine Netzwerk-/Live-/Paper-/Download-Pfade (statischer Scan).

## 8. Doku/README

- README v1-Parameterliste/Defaults-Tabelle: `max_signals_per_day` von „nicht
  erzwungen" auf „aktiv (None = deaktiviert)" aktualisieren.
- CLI-Abschnitt um `--max-signals-per-day` (v1-only) ergänzen, falls Option B.
- Teststand aktualisieren.
- `docs/lq-015-max-signals-per-day.md` um „Phase 2 Implementation Status".

## 9. Kompatibilität

- Default `None` = **keine** Änderung am bisherigen v1-Verhalten.
- v0 unverändert.
- Runner, RiskEngine, `BacktestResult`, `CostModel` unverändert.
- Keine Echtdaten, keine Reports.
- Einzige bewusste Änderung an Bestandstests: Ersatz des „not enforced"-Tests
  (§7). Phase 2 prüft zusätzlich, dass kein Test einen **exakten** v1-Params-Satz
  asseriert, der durch das zusätzliche `max_signals_per_day`-Feld in
  `strategy_metadata` bräche (nach aktuellem Stand assertieren die Tests nur
  Teilmengen/einzelne Schlüssel).

## 10. Offene Entscheidungspunkte

1. **Strategie-only oder Strategie+CLI in Phase 2?**
   → *Empfehlung: Strategie+CLI* (Option B; CLI kann v1-Parameter seit LQ-009
   sauber gaten).
2. **`max_signals_per_day` bei `None` in `strategy_metadata`?**
   → *Empfehlung: ja* (bei v1 als reproduzierbarer Parameter; `None` = deaktiviert,
   in README klarstellen).
3. **Vom Tageslimit verworfenes Signal → Cooldown?**
   → *Empfehlung: nein.*
4. **Tagesgrenze UTC oder lokal?**
   → *Empfehlung: UTC via `timestamp.date()` bei UTC-aware Testdaten.*
5. **Rejected-by-day-limit-Zähler einführen?**
   → *Empfehlung: nein* (neue Diagnostik; nicht Phase 2).
6. **`max_signals_per_day` in Comparison-Reports?**
   → *Empfehlung: automatisch ja*, wenn es in `strategy_metadata.params`
   vorhanden ist (Comparison-Renderer iteriert `params` bereits generisch).

---

## Phase 2 Implementation Status

Umgesetzt (Option B: Strategie + CLI):

- **`max_signals_per_day` in `MidBreakoutStrategyV1` aktiv:** Zählung je
  UTC-Kalendertag über `bars[i].timestamp.date()`; nach `N` erzeugten Signalen
  eines Tages werden weitere übersprungen; Reset am nächsten UTC-Tag.
- **Default `None` bleibt rückwärtskompatibel** (Verhalten unverändert; v0 nicht
  berührt). Konstruktor-Validierung (`None` oder `> 0`) war bereits vorhanden.
- **Tageslimit = letztes Gate vor dem Append**; ein dadurch verworfenes Signal
  erhöht den Zähler **nicht** und löst **keinen** Cooldown aus (`next_allowed`
  bleibt unverändert) — durch einen Cross-Day-Test abgesichert.
- **CLI-Flag `--max-signals-per-day INT`** (Default `None`) implementiert, **nur**
  für `--strategy v1`. Bei `strategy=v0` (auch Default-v0 ohne `--strategy`) wird
  ein gesetzter Wert **hart abgelehnt** (Usage-Exit, keine Report-Datei).
  Validierung (nur v1): `> 0`.
- **`strategy_metadata.params` (v1)** enthält `max_signals_per_day` (auch `None`
  = deaktiviert, als reproduzierbarer Parameter); bei v0 **nicht** enthalten.
- **Terminal-Hinweis** (v1) um `max_signals_per_day=…` ergänzt.
- **Tests:** `tests/test_strategy_v1.py` (alter „not enforced"-Test **ersetzt**
  durch 6 Enforcement-Tests: None-Regression, Limit=1/=2 am selben Tag, Reset am
  Folgetag, Cooldown-Isolation, Determinismus) und
  `tests/test_cli_strategy_selection.py` (+7: Akzeptanz, v0-Gating, Default-v0-
  Gating, 0/negativ abgelehnt, Report enthält/omittet das Feld).
- **pytest: 333 passed** (lokale `.venv`).

v0-Strategie, Runner, RiskEngine, CostModel/metrics unverändert. Kein Push.

Keine Profitabilitätsaussage, keine Echtdatenbewertung.

---

*Research-/Backtesting-Kontext. Keine Live-/Paper-Trading-Funktion, keine
Exchange-Anbindung, keine Profitabilitätsaussage, keine Handelsempfehlung.*
