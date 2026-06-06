# LQ-009 — CLI Strategy Selection

> Status: **Phase 2 implementiert** (siehe „Phase 2 Implementation Status" unten).
> Phase 1 war die hier dokumentierte Spezifikation; Phase 2 hat sie in
> `src/liquent/cli/backtest_mid_breakout.py` umgesetzt.

## 1. Ausgangslage

- Die bestehende CLI `src/liquent/cli/backtest_mid_breakout.py` instanziiert
  **fest** `MidBreakoutStrategy` (v0) — siehe Instanziierung mit
  `min_strength=0.0` und `allow_short=args.allow_short`. Es gibt aktuell **kein**
  `--strategy`-Flag.
- LQ-008 hat `MidBreakoutStrategyV1` **additiv** eingeführt
  (`src/liquent/strategy/mid_breakout_v1.py`), inkl. Tests
  (`tests/test_strategy_v1.py`) und Export in `src/liquent/strategy/__init__.py`.
- **v0 bleibt Regressionsbasis** und wird nicht verändert.
- **v1 ist implementiert und getestet**, aber noch **nicht über die CLI
  auswählbar**.
- `BacktestRunner` und `RiskEngine` bleiben **unabhängig** von der konkreten
  Strategie, solange die injizierte Strategie die Schnittstelle
  `generate_signals(market_data) -> Sequence[Signal]` erfüllt (beide Klassen tun
  das). Die Strategieauswahl ist damit rein eine CLI-/Verdrahtungsfrage — kein
  Eingriff in Runner oder Risk-Gate.

### Ist-Defaults der bestehenden CLI (verifiziert)

| CLI-Argument | Ist-Default (v0-CLI) | Typ/Form |
|---|---|---|
| `--lookback-bars` | `3` | `int` |
| `--stop-distance-pct` | `0.05` | `float` |
| `--allow-short` | `True` | Bool-Wert `true\|false\|1\|0\|yes\|no` |
| `--min-strength` | **existiert nicht** (im Code hart `0.0`) | — |
| `--strategy` | **existiert nicht** | — |

> **Wichtig (Abweichung):** Die CLI besitzt heute **kein** `--min-strength` und
> verdrahtet `min_strength=0.0` direkt. Außerdem ist `--allow-short` als
> **Bool-Wert** umgesetzt (`--allow-short false`), **nicht** als
> `--no-allow-short`-Schalter. Beides ist in Abschnitt 4/10 als
> Entscheidungspunkt vermerkt.

## 2. Ziel

Eine **explizite** Strategieauswahl auf der CLI:

```text
--strategy v0|v1
```

`v0` bleibt zunächst **Default**, damit bestehende CLI-Läufe **byte-identisch
reproduzierbar** bleiben (der Report ist deterministisch; ein geänderter Default
würde bestehende Vergleichsläufe brechen).

Begründung:
- **Rückwärtskompatibilität** — vorhandene Aufrufe ohne `--strategy` verhalten
  sich exakt wie heute.
- **Vergleichbarkeit** mit bisherigen 1-Tages-/30-Tage-Läufen (v0).
- **Sichere, schrittweise Einführung** von v1 ohne stillen Verhaltenswechsel.

## 3. CLI-Parameter

**Allgemein (beide Strategien):**

```text
--strategy v0|v1            (neu; Default v0)
--lookback-bars             (bestehend)
--stop-distance-pct         (bestehend)
--allow-short true|false    (bestehend; Form beibehalten, siehe Entscheidungspunkt 2/§10)
--min-strength              (neu; heute nicht vorhanden — siehe Entscheidungspunkt)
```

**Nur v1-relevant:**

```text
--breakout-threshold-pct    (neu; nur strategy=v1)
--cooldown-bars             (neu; nur strategy=v1)
```

**Optional später (nicht in LQ-009 Phase 2):**

```text
--max-signals-per-day       (erst v1.1 / spätere Phase; in v1 ohnehin nicht erzwungen)
```

**Wirksamkeitsregel:**
- `--breakout-threshold-pct` und `--cooldown-bars` sind **nur** für `strategy=v1`
  gültig.
- Verhalten bei `strategy=v0` mit gesetzten v1-only-Parametern — zwei Optionen:

  - **Option A — ignorieren mit Warnung:** v1-only-Parameter werden bei v0
    akzeptiert, aber ignoriert; die CLI gibt eine Warnung auf `stderr` aus.
    - *Nachteil:* Scheinsicherheit — der Nutzer glaubt, ein Threshold/Cooldown
      sei aktiv, obwohl v0 ihn nicht kennt. Reports könnten missverstanden
      werden. Verschlechtert die Reproduzierbarkeit (gleicher Aufruf, anderes
      mentales Modell).
  - **Option B — hart ablehnen (Exit-Code „Usage"):** v1-only-Parameter bei
    `strategy=v0` führen zu einem klaren Fehler und Programmabbruch, bevor
    gerechnet wird.
    - *Vorteil:* eindeutig, keine stillen Annahmen, reproduzierbar.

> **Empfehlung: Option B (hart ablehnen).** Begründung: verhindert
> Scheinsicherheit, verhindert Missverständnisse, hält CLI-Läufe eindeutig
> reproduzierbar. Technisch sauber über einen Sentinel-Default (z. B. `None`)
> erkennbar: ist ein v1-only-Argument bei `strategy=v0` **explizit gesetzt**
> (`is not None`), wird mit Usage-Exit abgelehnt.

## 4. Default-Verhalten

- **Default-`strategy` = v0** (zunächst).
- **v0** nutzt die **bestehenden CLI-Defaults** (`lookback_bars=3`,
  `stop_distance_pct=0.05`, `allow_short=True`, `min_strength=0.0`).
- **v1** soll die **Defaults aus `MidBreakoutStrategyV1`** abbilden:
  - `lookback_bars=12`
  - `stop_distance_pct=0.01`
  - `breakout_threshold_pct=0.001`
  - `cooldown_bars=3`
  - `allow_short=True`
  - `min_strength=0.0`
  - `max_signals_per_day=None` (in Phase 2 **nicht** aktiv/erzwungen)

### Entscheidungspunkt: divergierende Defaults (verifiziert)

Die **bestehenden CLI-Defaults** für die *gemeinsamen* Parameter weichen von den
**v1-Strategie-Defaults** ab:

| Parameter | v0-CLI-Default | v1-Strategie-Default |
|---|---|---|
| `lookback_bars` | `3` | `12` |
| `stop_distance_pct` | `0.05` | `0.01` |

Da `--lookback-bars` und `--stop-distance-pct` **gemeinsame** Argumente mit
**einem** statischen argparse-Default sind, würde `--strategy v1` **ohne**
weitere Maßnahme die **v0-Defaults** (3 / 0.05) erben — **nicht** die
v1-Defaults (12 / 0.01). Lösungsoptionen (in Phase 2 zu entscheiden):

1. **Sentinel-Defaults + strategieabhängige Auflösung (empfohlen):** gemeinsame
   Argumente erhalten `default=None`; nach dem Parsen werden nicht gesetzte Werte
   je nach `--strategy` auf den jeweiligen Strategie-Default aufgelöst. So bekommt
   `--strategy v1` automatisch 12 / 0.01, `--strategy v0` bleibt bei 3 / 0.05.
   Bestehende v0-Aufrufe bleiben byte-identisch.
2. **Statische Defaults beibehalten + dokumentieren:** ein Default-Satz für beide;
   der Nutzer muss bei v1 die v1-Werte explizit setzen. Einfacher, aber
   fehleranfällig und überraschend.

> **Empfehlung: Option 1 (Sentinel-Defaults).** Bewahrt v0-Reproduzierbarkeit
> *und* liefert v1 die spezifizierten Defaults.

> **Zusätzlicher Entscheidungspunkt `--min-strength`:** Da die CLI heute kein
> solches Argument hat, ist dessen Einführung neu. Bis dahin verdrahtet die CLI
> `min_strength=0.0`. Empfehlung: `--min-strength` als gemeinsames Argument mit
> Default `0.0` einführen (gilt für v0 und v1 gleich), damit die Pseudo-Logik in
> §6 unverändert nutzbar ist.

## 5. Validierung (CLI-Ebene, früh)

Geplante Prüfungen **vor** der Instanziierung (klare Fehlermeldungen, Usage-Exit):

- `strategy` ∈ {`v0`, `v1`} (über argparse `choices`).
- `lookback_bars > 0`.
- `0 < stop_distance_pct < 1`.
- `0 <= min_strength <= 1`.
- `breakout_threshold_pct` **nur bei v1** erlaubt; Wertebereich
  `0 <= breakout_threshold_pct < 0.1`.
- `cooldown_bars` **nur bei v1** erlaubt; `cooldown_bars >= 0`.
- `max_signals_per_day`: in Phase 2 **nicht** implementieren (oder nur als
  „reserviert für spätere Phase" dokumentieren).

> **Wichtig:** Die **finale, autoritative Validierung bleibt** in den
> Strategie-Konstruktoren (`MidBreakoutStrategy` / `MidBreakoutStrategyV1`)
> erhalten (fail-safe; sie werfen `ValueError`). Die CLI validiert **zusätzlich
> und früh**, um nutzerfreundliche Meldungen mit Usage-Exit-Code zu liefern,
> bevor Daten geladen/gerechnet werden. Doppelte Validierung ist beabsichtigt:
> die CLI darf nie der einzige Schutz sein.

## 6. Instanziierungslogik (Plan für Phase 2)

```python
if args.strategy == "v0":
    strategy = MidBreakoutStrategy(
        lookback_bars=args.lookback_bars,
        stop_distance_pct=args.stop_distance_pct,
        allow_short=args.allow_short,
        min_strength=args.min_strength,
    )
elif args.strategy == "v1":
    strategy = MidBreakoutStrategyV1(
        lookback_bars=args.lookback_bars,
        stop_distance_pct=args.stop_distance_pct,
        breakout_threshold_pct=args.breakout_threshold_pct,
        cooldown_bars=args.cooldown_bars,
        allow_short=args.allow_short,
        min_strength=args.min_strength,
    )
```

Hinweise:
- Setzt voraus, dass `--min-strength` als CLI-Argument existiert (siehe §4).
- Bei Sentinel-Defaults (§4 Option 1) werden `args.lookback_bars` /
  `args.stop_distance_pct` zuvor strategieabhängig aufgelöst.
- v1-only-Argumente (`breakout_threshold_pct`, `cooldown_bars`) werden bei
  `strategy=v0` **nicht** durchgereicht und bei explizitem Setzen vorher
  abgelehnt (§3 Option B).

## 7. Reporting (Anforderung, keine Implementierung in Phase 1)

Künftige CLI-Ausgaben/Reports sollen die gewählte Strategie **eindeutig**
ausweisen:

- `strategy_name` (z. B. `MidBreakoutStrategy` / `MidBreakoutStrategyV1` — der
  Runner schreibt bereits `type(self.strategy).__name__` in
  `parameters["strategy"]`),
- `strategy_version` bzw. `strategy_key` (`v0` / `v1`),
- `strategy_params` (die effektiv verwendeten Strategie-Parameter).

> **Wichtig:** Keine Report-Implementierung in Phase 1. Falls die Erweiterung des
> bestehenden deterministischen Report-Aufbaus nicht trivial ist, wird sie als
> **separate Reporting-Teilaufgabe** geführt (siehe Entscheidungspunkt 4). Der
> Report muss deterministisch bleiben (keine Wall-Clock, kein Zufall).

## 8. Tests für spätere Phase 2

- Default ohne `--strategy` bleibt **v0** (Instanz ist `MidBreakoutStrategy`).
- `--strategy v0` instanziiert `MidBreakoutStrategy`.
- `--strategy v1` instanziiert `MidBreakoutStrategyV1`.
- v1-only-Parameter bei `--strategy v0` werden **abgelehnt** (Usage-Exit).
- `--strategy v1 --breakout-threshold-pct …` wird akzeptiert.
- `--strategy v1 --cooldown-bars …` wird akzeptiert.
- ungültige `--strategy` (z. B. `v2`) wird abgelehnt.
- ungültiger `--breakout-threshold-pct` (z. B. `0.2`) wird abgelehnt.
- ungültiger `--cooldown-bars` (z. B. `-1`) wird abgelehnt.
- **bestehende CLI-Tests bleiben grün** (v0-Pfad byte-identisch).
- keine Netzwerk-/Live-/Paper-Trading-Pfade (statischer Scan wie bestehend).

## 9. Nicht-Ziele (LQ-009 Phase 1)

- keine Implementierung,
- keine CLI-Code-Änderung,
- keine Echtdatenläufe,
- keine Reports erzeugen,
- keine Kostenmodell-Erweiterung,
- keine Parameter-Suche,
- keine Optimierung,
- kein Paper-Trading,
- kein Live-Trading,
- keine Exchange-API,
- keine Profitabilitätsbewertung,
- keine Trading-Empfehlung,
- kein Push.

## 10. Offene Entscheidungspunkte

1. **Soll v0 Default bleiben oder später auf v1 wechseln?**
   → *Empfehlung: vorerst v0* (Reproduzierbarkeit). Ein späterer Wechsel auf v1
   wäre ein bewusster, dokumentierter Breaking-Change.
2. **v1-only-Parameter bei `strategy=v0`: hart ablehnen oder ignorieren?**
   → *Empfehlung: hart ablehnen* (Option B, §3).
3. **`max_signals_per_day` schon in Phase 2 CLI-seitig sichtbar machen?**
   → *Empfehlung: nein* — erst v1.1 / spätere Phase (in v1 ohnehin nicht
   erzwungen).
4. **CLI-Reports um `strategy_params` erweitern?**
   → *Empfehlung: ja*, aber als **separate Reporting-Teilaufgabe**, falls der
   aktuelle Report-Aufbau nicht trivial erweiterbar ist.
5. **(Neu, verifiziert) Divergierende gemeinsame Defaults (3/0.05 vs. 12/0.01):**
   → *Empfehlung: Sentinel-Defaults* mit strategieabhängiger Auflösung (§4
   Option 1).
6. **(Neu, verifiziert) `--min-strength` & `--allow-short`-Form:**
   → `--min-strength` neu einführen (Default `0.0`, gemeinsam). `--allow-short`
   in der **bestehenden Bool-Wert-Form** beibehalten (`--allow-short false`)
   statt `--no-allow-short`, um die aktuelle CLI-Konvention nicht zu brechen.

---

## Phase 2 Implementation Status

Umgesetzt in `src/liquent/cli/backtest_mid_breakout.py` (LQ-009 Phase 2):

- `--strategy v0|v1` implementiert (argparse `choices`).
- **Default bleibt v0** — bestehende Aufrufe verhalten sich byte-identisch.
- **Sentinel-Logik** umgesetzt: gemeinsame Parameter (`--lookback-bars`,
  `--stop-distance-pct`, `--min-strength`) haben Default `None` und werden
  strategieabhängig aufgelöst (v0: 3 / 0.05 / 0.0; v1: 12 / 0.01 / 0.0).
- **v1-only Parameter** (`--breakout-threshold-pct`, `--cooldown-bars`) bei
  `strategy=v0` **hart abgelehnt** (Usage-Fehler, keine Report-Datei) —
  inklusive Default-v0 ohne explizites `--strategy`.
- **v1-Defaults** (`breakout_threshold_pct=0.001`, `cooldown_bars=3`) werden
  **nur bei `strategy=v1`** aufgelöst.
- **`--min-strength`** neu eingeführt (Default `0.0`, gemeinsam).
- **`--allow-short`** in der bestehenden Bool-Wert-Form beibehalten
  (`--allow-short true|false`), kein `--no-allow-short` (Entscheidungspunkt 6).
- **Terminal-Hinweis** (`strategy: …`-Zeile) auf stdout ergänzt.
- **Markdown-Report nicht refaktoriert** — er trägt den Strategie-Klassennamen
  bereits über `parameters["strategy"]` (Reporting-Erweiterung um
  `strategy_params` bleibt offene, separate Teilaufgabe — Entscheidungspunkt 4).
- `BacktestRunner` und `RiskEngine` unverändert; v0/v1-Strategieklassen
  unverändert.
- **Tests ergänzt:** `tests/test_cli_strategy_selection.py` (15 Tests);
  bestehende CLI-Tests bleiben grün.
- **pytest: 261 passed** (lokale `.venv`).
- **Kein Push.**

Hinweis zur Fehlerbehandlung: Das v1-only Gating folgt dem bestehenden CLI-Stil
(Meldung auf `stderr` + Exit-Code „Usage"), damit `main(argv)` weiterhin einen
Int-Exit-Code liefert (statt `parser.error(...)`, das `SystemExit` auslöst).

Keine Profitabilitätsaussage, keine Echtdatenbewertung.

---

*Research-/Backtesting-Kontext. Keine Live-/Paper-Trading-Funktion, keine
Exchange-Anbindung, keine Profitabilitätsaussage, keine Handelsempfehlung.*
