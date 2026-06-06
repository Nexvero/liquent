# LQ-021 — Visual Preview UI Polish and Signal Chart

> Status: **Phase 1 — Spezifikation / Dokumentation.** Keine Implementierung,
> keine Dependency-Installation, keine `tools/`-Änderung, keine Echtdaten. Plant
> die visuelle Verbesserung der lokalen Visual Preview (Mid-Preis-Chart +
> klarere UI). Rein technische Darstellung — keine Profitabilitätsbewertung,
> keine Trading-Empfehlung.

## 1. Ausgangslage

- LQ-019 hat `tools/visual_preview/` (`preview_logic.py`, `app.py`) eingeführt.
- LQ-020 hat Streamlit als **optionales Extra** `visual` ergänzt + Run
  Instructions dokumentiert.
- Die Preview ist weiterhin **lokal, optional, synthetisch**; bisher Fokus auf
  Funktionsfähigkeit/Sicherheit.
- Jetzt soll die Preview **visuell verständlicher** werden: klareres Layout,
  technische KPIs, Signaltabelle, einfacher **Mid-Preis-Chart mit
  Signalmarkern**, sichtbare Safety-Hinweise.

### Verifizierte Fakten (bindend für Phase 2)

- **Weder Streamlit noch Altair installiert**
  (`find_spec("streamlit")/("altair")` → None). → Ein Chart **ohne neue
  Dependency** geht nur über **Streamlit-native** Funktionen (`st.line_chart`);
  Altair/Plotly würden ein Extra erfordern (siehe §5).
- Vorhandene `preview_logic`-API: `SAFETY_NOTES`, `PreviewDataset`,
  `build_preview_datasets`, `build_strategy`, `generate_preview_summary`. Die
  Chart-Helfer (§6) sind **additiv**; `generate_preview_summary` bleibt
  rückwärtskompatibel.
- `app.py` importiert Streamlit **nur** in `main()`; Tests laufen **ohne**
  Streamlit (bleibt so).

Visualisierung ist rein technische Darstellung — keine Trading-Entscheidung,
keine Profitabilitätsbewertung, keine Empfehlung.

## 2. Ziel

Eine bessere lokale UI-Preview für **synthetische** Datensätze, die technisch
sichtbar macht: gewähltes Dataset, Strategie v0/v1, wirksame Parameter,
`signals_total`, Signalrichtung (Long/Short), Signalzeitpunkte, Signal-/Mid-
Preise, `stop_price` (als technische Sizing-Info), `strength`, sowie die Wirkung
von `cooldown_bars` und `max_signals_per_day`.

## 3. Nicht-Ziele

keine Echtdaten · kein CSV-Upload in dieser Phase · kein Download · keine
API-/Exchange-Anbindung · kein Paper-Trading · kein Live-Trading · keine
Orderfunktion · kein Deployment · kein Login/Auth · keine Reportdateien · keine
automatische Speicherung · keine Optimierung/Parameter-Suche · keine
Profitabilitätsbewertung · keine Trading-Empfehlung · **kein Equity-Chart** ·
**kein `ending_equity` prominent** · keine Änderung an Strategie-/Runner-/
RiskEngine-Kernlogik.

## 4. UI-Struktur

### Header
- Titel: „Liquent — understand liquidity".
- Untertitel: „Local visual preview for synthetic signal inspection".
- **Safety-Banner:** „Synthetic/local preview only", „No live trading",
  „No trading recommendation", „No profitability assessment".

### Sidebar (Gruppen)
1. **Dataset:** `micro_long`, `micro_short`, `stair_cooldown`.
2. **Strategy:** `v0`, `v1`.
3. **Shared Parameters:** `lookback_bars`, `stop_distance_pct`, `allow_short`,
   `min_strength`.
4. **v1 Parameters:** `breakout_threshold_pct`, `cooldown_bars`,
   `max_signals_per_day` — bei v0 deaktiviert/klar nicht angewendet.
5. **Cost Parameters:** in Phase 2 nur **anzeigen/vorbereiten**; da die Preview
   `generate_signals` **ohne Runner** nutzt, als
   „not used in signal-only preview" kennzeichnen.

### Main Content
1. **Technical Summary:** dataset name, strategy key, `signals_total`, bars,
   first timestamp, last timestamp.
2. **Signal Chart:** Mid-Serie als Linie; Long-/Short-Signale als Marker (visuell
   unterscheidbar, soweit ohne Extra möglich); **kein** Equity, **kein**
   Profit/Performance.
3. **Signal Table:** timestamp, side, price, stop_price, strength.
4. **Strategy Metadata:** Parameter-Tabelle.
5. **Safety Notes.**

## 5. Chart-Technologie

### Option A — Streamlit-native `line_chart` + Tabellen
- *Pro:* **keine** neue Dependency, sehr einfach, Charting bereits in Streamlit.
- *Contra:* Signalmarker schwerer sauber im selben Chart; weniger Kontrolle.

### Option B — Altair über Streamlit
- *Pro:* Marker kontrollierbarer.
- *Contra:* **Altair ist nicht installiert** (verifiziert) → zusätzliche
  Dependency-Frage.

### Option C — Plotly
- *Pro:* interaktiv, klare Marker.
- *Contra:* neue Dependency; für Phase 2 zu schwer.

> **Empfehlung: Option A** für Phase 2 — **kein** neues Chart-Paket. Mid-Chart
> via `st.line_chart`; lassen sich Long/Short-Marker nicht sauber in derselben
> Linie darstellen, dann:
> - Mid-Chart (`st.line_chart`), darunter die Signal-Tabelle,
> - optional eine separate Long/Short-Marker-Darstellung (z. B. zweite/dritte
>   Chart-Spalte mit `long_signal_price`/`short_signal_price`, die `line_chart`
>   als zusätzliche Serien zeichnet — Lücken bleiben leer).
>
> `preview_logic.py` bereitet eine **chartfreundliche** Datenstruktur vor (§6);
> die App nutzt zunächst einfache Tabellen/`line_chart`.

## 6. Preview-Logic-Erweiterung (testbar, ohne Streamlit)

Neue, **reine** Funktionen in `tools/visual_preview/preview_logic.py` (keine
Streamlit-/Plotly-/Matplotlib-Importe, deterministisch, keine I/O):

```python
def build_price_rows(dataset: PreviewDataset) -> list[dict[str, Any]]:
    # je Bar: timestamp, mid, bid, ask, volume

def build_signal_rows(signals) -> list[dict[str, Any]]:
    # je Signal: timestamp, side, price, stop_price, strength

def build_chart_rows(dataset, signals) -> list[dict[str, Any]]:
    # je Bar: timestamp, mid, long_signal_price (optional), short_signal_price (optional)
```

- `build_chart_rows` setzt `long_signal_price`/`short_signal_price` nur an Bars
  mit passendem Signal (sonst `None`), sodass eine Chart-Bibliothek Marker als
  separate Serien zeichnen kann.
- `price` der Signalzeilen = Mid am Signal-Bar (wie in
  `generate_preview_summary` bereits berechnet).

## 7. App-Erweiterung Phase 2 (`tools/visual_preview/app.py`)

- Sidebar in Gruppen gliedern; Safety-Banner oben.
- `st.metric` für technische Kennzahlen (`signals_total`, bars).
- `st.dataframe`/`st.table` für die Signal-Tabelle.
- `st.line_chart` für Mid-Preis (falls Streamlit verfügbar).
- Strategy-Metadaten als Tabelle.
- **Keine** Reportdateien, **keine** Netzwerk-Calls, **kein** CSV-Upload.
- **App bleibt ohne Streamlit importierbar** (Lazy-Import in `main()`); Tests
  brauchen kein Streamlit.

## 8. Tests für Phase 2 (ohne Streamlit-E2E)

1. `build_price_rows` liefert je Bar `timestamp/mid/bid/ask/volume`.
2. `build_signal_rows` liefert `timestamp/side/price/stop_price/strength`.
3. `build_chart_rows` liefert Mid-Werte + Signalmarker-Felder.
4. Long-/Short-Signale werden korrekt markiert
   (`long_signal_price`/`short_signal_price` an den richtigen Bars).
5. **Keine** Profitabilitätsfelder (`profit`, `performance`, `ending_equity`,
   `winner`, `better`, `worse`) in den Chart-/Signal-Datenstrukturen.
6. `generate_preview_summary` bleibt rückwärtskompatibel (gleiche Felder).
7. `max_signals_per_day` bleibt sichtbar (None/1/2 → 5/1/2 auf `stair_cooldown`).
8. `tools.visual_preview.app` bleibt **ohne Streamlit importierbar**.
9. Statischer Scan: keine Netzwerk-/Download-/API-/Exchange-/Paper-/Live-Pfade.
10. README erwähnt Chart/Signal-Table, **ohne** Ergebnisinterpretation.
11. Bestehende Tests bleiben grün.

## 9. README/Doku-Auswirkung

README „Visual Preview" ergänzen: enthält nun Technical Summary, Mid-price chart,
Signal table, Strategy metadata, Safety notes — **weiterhin**: synthetic/local
preview only, no live trading, no trading recommendation, no profitability
assessment, no CSV upload yet, no report files. Teststand nach Phase 2
aktualisieren.

## 10. Sicherheitsgrenzen

keine API-Keys · keine Exchange-Credentials · keine Netzwerk-Calls · kein
Download · keine Live-Daten · keine Orders · keine Paper-Trading-Verbindung ·
keine Reportdateien · keine gespeicherten Nutzerdaten · keine
Profitabilitätsbewertung · keine Empfehlungssprache · **keine Equity-/
Performance-Darstellung im MVP**.

## 11. Kompatibilität

- `preview_logic.py` bleibt Streamlit-frei; `app.py` bleibt ohne Streamlit
  importierbar (Lazy-Import in `main()`).
- **Keine** neue Pflicht-Dependency (Option A nutzt Streamlit-natives Charting;
  Streamlit bleibt optionales Extra).
- Keine Änderung an Strategien/Runner/RiskEngine/CLI.
- Keine Änderung an bestehenden Tests außer Ergänzung neuer Tests.
- Bestehende Visual-Preview-Funktionen bleiben erhalten.

## 12. Offene Entscheidungspunkte

1. **Streamlit-native Chart oder zusätzliche Chart-Library?**
   → *Empfehlung: Streamlit-native* (keine neue Dependency; Altair/Plotly nicht
   installiert).
2. **Signalmarker im Chart oder Tabelle darunter?**
   → *Empfehlung:* Chart-Daten vorbereiten (`build_chart_rows`), Tabelle sicher
   anzeigen; Marker nur, falls ohne Extra sauber möglich.
3. **Cost Parameters im UI aktiv oder nur sichtbar?**
   → *Empfehlung: nur sichtbar* als „not used in signal-only preview"
   (kein Runner).
4. **CSV-Upload?** → *Empfehlung: nein*, spätere Phase.
5. **Runner in Preview integrieren?** → *Empfehlung: nein*, spätere Phase.
6. **Screenshot erstellen?** → *Empfehlung: nein*, keine Artefakte.

---

## Phase 2 Implementation Status

Umgesetzt (Option A, keine neue Dependency, kein Runner):

- **`preview_logic.py`** (Streamlit-frei) um drei reine, deterministische Builder
  erweitert: `build_price_rows` (timestamp/mid/bid/ask/volume),
  `build_signal_rows` (timestamp/side/price/stop_price/strength; `price` via
  `mid_by_ts`), `build_chart_rows` (mid + `long_signal_price`/`short_signal_price`
  nur am Signal-Bar, sonst `None`).
- **`generate_preview_summary`** additiv erweitert: zusätzlich `price_rows`,
  `chart_rows`, `technical_summary` (dataset_name/strategy_key/bars/signals_total/
  first_timestamp/last_timestamp). Die bestehenden Felder
  (`dataset/strategy/signals_total/signals/safety_notes`) bleiben — `signals`
  wird intern über `build_signal_rows` erzeugt (identische Ausgabe). **Keine**
  Profitabilitäts-/Performance-Felder.
- **`app.py`** UI-Politur in `main()`: Header + Untertitel, Safety-Banner (alle 4
  Notes), gegliederte Sidebar (Dataset/Strategy/Shared/v1/Cost mit „not used in
  signal-only preview"), Technical Summary via `st.metric`/`st.columns`,
  Mid-Chart via `st.line_chart(chart_rows, x="timestamp", y=[mid,
  long_signal_price, short_signal_price])`, Signal-Table via `st.dataframe`,
  Strategy-Metadata-Tabelle, Safety-Notes. Streamlit-Import bleibt **lazy** in
  `main()`; App ohne Streamlit importierbar; kein Equity-/ending_equity.
- **Keine neue Dependency**, kein Runner, keine Echtdaten, keine Reportdateien.
- **Tests:** `tests/test_visual_preview_chart_logic.py` (9) + Anpassung des
  Summary-Struktur-Tests (Superset statt exakt). Bestehende Tests grün.
- **pytest: 379 passed** (lokale `.venv`); `app` ohne Streamlit importierbar,
  Fallback-Meldung unverändert.

`src/`, CLI, Runner, RiskEngine, Strategien, `pyproject.toml` unverändert.
Kein Push.

---

*Research-/Backtesting-Kontext. Keine Live-/Paper-Trading-Funktion, keine
Exchange-Anbindung, keine Profitabilitätsaussage, keine Handelsempfehlung.*
