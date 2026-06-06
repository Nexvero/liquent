# LQ-022 — Visual Preview Local CSV Upload

> Status: **Phase 1 — Spezifikation / Dokumentation.** Keine Implementierung,
> keine Dependency-Installation, keine `tools/`-Änderung, keine Echtdaten, keine
> CSV im Repo. Plant einen **lokalen, optionalen** CSV-Modus für die Visual
> Preview. Rein technische Darstellung — keine Profitabilitätsbewertung, keine
> Trading-Empfehlung.

## 1. Ausgangslage

- LQ-019 hat die lokale Visual Preview eingeführt; LQ-020 hat Streamlit als
  optionales Extra dokumentiert; LQ-021 hat UI-Polish, Technical Summary, Signal
  Table und Chart-Daten ergänzt.
- Die Preview nutzt aktuell **nur synthetische** Datasets.
- Nächster sinnvoller Schritt: **optionales Laden lokaler CSV-Dateien**.
- Es darf **keine** automatische Echtdatenquelle, **kein** Download, **keine**
  Exchange-/API-Anbindung entstehen.

### Verifizierte Fakten (bindend für Phase 2)

- `MarketData` hat die Felder `timestamp, bid, ask, volume` (kein OHLC);
  `PreviewDataset` = `name/description/mids/market_data`.
- Die **bestehende** `src/liquent/data/HistoricalFileSource` nutzt ein **anderes**
  Schema: OHLCV `timestamp,open,high,low,close,volume` mit `close → bid = ask =
  close` (mid = close), stdlib `csv` + `fromisoformat`.
- **Der Preview-CSV-Parser ist davon getrennt** (Tools-lokal, minimal bid/ask) und
  ändert `src/` **nicht** (siehe §5/§12.7).

CSV-Upload ist nur ein lokaler Analyse-/Preview-Modus — keine Trading-
Entscheidung, keine Profitabilitätsbewertung, keine Empfehlung.

## 2. Ziel

Ein sicherer lokaler CSV-Modus für die Visual Preview, der:
- lokale CSV-Dateien (Streamlit `file_uploader` oder CSV-Text) laden kann,
- daraus `MarketData` erzeugt,
- **dieselbe** Preview-Logik wie synthetische Datasets nutzt (Technical Summary,
  Chart, Signal Table),
- **keine** CSV im Repo speichert, **keine** Datei automatisch schreibt, **keine**
  Netzwerkverbindung nutzt.

> **Empfehlung:** Phase 2 implementiert primär einen **testbaren CSV-Text-Parser**
> (`build_dataset_from_csv_text`) + eine einfache `file_uploader`-Anbindung in der
> App; der Parser arbeitet auf String/Bytes, **kein** File-I/O.

## 3. Nicht-Ziele

keine automatischen Echtdaten · kein Download · keine API-/Exchange-Anbindung ·
kein Broker · kein Paper-Trading · kein Live-Trading · keine Orders · **keine
Persistenz von Uploads** · **keine CSV im Repo** · keine Reportdateien · kein
Deployment · kein Login/Auth · keine Optimierung/Parameter-Suche · keine
Profitabilitätsbewertung · keine Trading-Empfehlung · **keine Runner-Integration**
in dieser Phase (nicht zwingend) · keine Änderung an Strategie-/Runner-/
RiskEngine-Kernlogik.

## 4. CSV-Format

Minimales, preview-spezifisches Schema (passend zu `MarketData`/`PreviewDataset`):

**Pflichtspalten:** `timestamp`, `bid`, `ask`. **Optional:** `volume`.

```csv
timestamp,bid,ask,volume
2026-01-01T00:00:00+00:00,100.0,100.5,1.0
```

- **`volume` fehlt → Default `1.0`** (konsistent mit den synthetischen Buildern).
- **Timestamp:** ISO-8601, **timezone-aware UTC** bevorzugt. **Naive Timestamps
  werden abgelehnt** (Fehlermeldung) — kein stilles Umdeuten. Tests nutzen
  UTC-aware ISO-Strings.
- **Validierung (fail-safe, `ValueError`):**
  - CSV nicht leer; Pflichtspalten vorhanden,
  - `bid`/`ask` numerisch, `bid > 0`, `ask > 0`, `ask >= bid`,
  - `timestamp` parsebar (`datetime.fromisoformat`) **und** tz-aware,
  - **Sortierung:** stabil **nach `timestamp` aufsteigend** (dokumentiert).
- `mid = (bid + ask) / 2` je Bar (wie synthetisch).

## 5. Ablage/Architektur

### Option A — Parser in `tools/visual_preview/preview_logic.py`
- *Pro:* lokal zur Preview, **keine** `src/`-Änderung, einfach testbar, keine
  Produktiv-API.
- *Contra:* Parsing-Logik nicht im Kernpaket.

### Option B — Parser in `src/liquent/data/`
- *Pro:* wiederverwendbar, näher an der Data Foundation.
- *Contra:* Produktivcode-Änderung; höhere Verantwortung fürs Format; mehr
  Tests/Kompatibilität (zudem nutzt `HistoricalFileSource` das **OHLCV**-Schema,
  nicht bid/ask → Vermischungsrisiko).

> **Empfehlung: Option A** für Phase 2. Begründung: Visual Preview bleibt Tooling;
> CSV-Upload ist UI-/Preview-Funktion; **keine** Kernlogik anfassen. Ein sauberer
> Data-Source-Parser im Kernpaket kann später separat spezifiziert werden.

## 6. Vorgeschlagene Preview-Logic-Erweiterung (`tools/visual_preview/preview_logic.py`)

```python
def build_dataset_from_csv_text(name: str, csv_text: str) -> PreviewDataset: ...
# optional:
def _validate_csv_columns(fieldnames: Sequence[str]) -> None: ...
def _parse_timestamp(value: str) -> datetime: ...   # tz-aware Pflicht, sonst ValueError
```

- **stdlib `csv`** (kein pandas); **kein** File-I/O in der Parser-Funktion; keine
  Netzwerk-Calls; keine Echtdaten.
- Liefert ein `PreviewDataset`:
  - `name`: CSV-Dateiname/Platzhalter,
  - `description`: „Local CSV preview dataset",
  - `market_data`: `tuple[MarketData, ...]` (sortiert nach timestamp),
  - `mids`: `tuple[float, ...]` (= `(bid+ask)/2` je Bar).
- Danach funktionieren `build_price_rows`/`build_signal_rows`/`build_chart_rows`/
  `generate_preview_summary` **unverändert** auf dem CSV-Dataset.

## 7. App-Erweiterung Phase 2 (`tools/visual_preview/app.py`)

Sidebar „Dataset Mode": **Synthetic dataset** | **Local CSV upload**.
- **Synthetic:** bisherige Dataset-Auswahl.
- **CSV:** `st.file_uploader(type="csv")` → Inhalt **nur im Speicher** an
  `build_dataset_from_csv_text` geben; Validierungsfehler via `st.error`; **keine**
  Speicherung, **keine** automatische Datei.
- Streamlit bleibt **optional**; App ohne Streamlit importierbar; Tests brauchen
  kein Streamlit; kein Browser-Test.

## 8. Tests für Phase 2 (ohne Streamlit-E2E, CSV als String)

**Parser:**
1. gültige CSV (timestamp/bid/ask/volume) → `PreviewDataset`.
2. ohne `volume` → Default `1.0`.
3. leere CSV → abgelehnt.
4. fehlende Pflichtspalte → abgelehnt.
5. nicht-numerisches `bid`/`ask` → abgelehnt.
6. `bid <= 0` → abgelehnt.
7. `ask < bid` → abgelehnt.
8. naiver Timestamp → abgelehnt.
9. unsortierte CSV → nach `timestamp` sortiert.
10. `mids` korrekt berechnet (`(bid+ask)/2`).
11. `generate_preview_summary` funktioniert mit CSV-Dataset.

**App/Safety:**
12. `app.py` bleibt ohne Streamlit importierbar.
13. keine Datei wird geschrieben.
14. keine Netzwerk-/Download-/API-/Exchange-/Paper-/Live-Pfade (statischer Scan).
15. Safety Notes bleiben sichtbar.
16. bestehende Tests bleiben grün.

> CSV-Inhalte **als String**; keine echten CSVs; keine tmp-Dateien; kein pandas;
> kein Streamlit-E2E.

## 9. README/Doku-Auswirkung

README „Visual Preview" ergänzen: unterstützt künftig **Synthetic datasets** und
**Local CSV upload** (wenn Streamlit installiert). CSV-Format dokumentieren:

```csv
timestamp,bid,ask,volume
2026-01-01T00:00:00+00:00,100.0,100.5,1.0
```

Sicherheitsgrenzen: Upload bleibt lokal im App-Kontext, keine Speicherung, kein
Download, keine API, keine Exchange, keine Trading-Empfehlung. Keine echten
Datenpfade, keine Ergebnisinterpretation. Teststand nach Phase 2 aktualisieren.

## 10. Sicherheitsgrenzen

keine API-Keys · keine Exchange-Credentials · keine Netzwerk-Calls · kein
Download · keine Live-Datenquelle · keine Orders · keine Paper-Trading-
Verbindung · **keine Speicherung hochgeladener CSVs** · keine Reportdateien ·
keine Profitabilitätsbewertung · keine Empfehlungssprache · keine Equity-/
Performance-Darstellung.

## 11. Kompatibilität

- Synthetische Datasets bleiben unverändert.
- `preview_logic.py` bleibt Streamlit-frei; `app.py` bleibt ohne Streamlit
  importierbar.
- **Keine** neue Pflicht-Dependency; **keine** `src/`-Änderung.
- Keine Änderung an Strategien/Runner/RiskEngine/CLI.
- Bestehende Tests bleiben grün.

## 12. Offene Entscheidungspunkte

1. **Naive Timestamps ablehnen oder als UTC interpretieren?**
   → *Empfehlung: ablehnen.*
2. **CSV-Parser in `tools` oder `src`?** → *Empfehlung: `tools`.*
3. **pandas verwenden?** → *Empfehlung: nein*, stdlib `csv`.
4. **CSV-Upload in Phase 2 UI aktivieren oder nur Parser?**
   → *Empfehlung: Parser + einfache UI-Anbindung*, ohne Speicherung.
5. **Lokaler Pfad zusätzlich zu `file_uploader`?**
   → *Empfehlung: nein* (in Phase 2 nur `file_uploader`, keine Pfadfreigaben).
6. **Volume-Default?** → *Empfehlung: `1.0`.*
7. **(Verifiziert) Schema bid/ask vs. OHLCV?** Der Rest von Liquent
   (`HistoricalFileSource`, CLI) nutzt OHLCV (`close → bid=ask=close`). Die
   Preview nutzt das **minimale bid/ask**-Schema (passt zu `PreviewDataset`).
   → *Empfehlung: bid/ask minimal* für die Preview; optionale OHLCV-Unterstützung
   (mit `close→bid=ask`) bleibt eine spätere Entscheidung. Bewusste, dokumentierte
   Divergenz.

---

## Phase 2 Implementation Status

Umgesetzt (Option A, keine neue Dependency, kein `src/`-Eingriff):

- **`build_dataset_from_csv_text(name, csv_text)`** in `preview_logic.py`
  (Streamlit-frei, stdlib `csv`, **kein** pandas, **kein** File-I/O,
  **kein** Netzwerk).
- **Pflichtspalten** `timestamp,bid,ask`; **optional `volume`** (Default `1.0`,
  wenn Spalte fehlt oder Feld leer).
- **Timestamp**: ISO-8601, **timezone-aware Pflicht** (`fromisoformat`); naive
  Timestamps → `ValueError`.
- **Validierung**: nicht leer, Pflichtspalten vorhanden, numerische `bid`/`ask`,
  `bid > 0`, `ask > 0`, `ask >= bid`, mind. eine Datenzeile; neutrale
  `ValueError`-Meldungen.
- **Sortierung** stabil nach `timestamp`; `mid = (bid + ask) / 2`.
- **`generate_preview_summary`** akzeptiert nun **str-Key ODER `PreviewDataset`**
  → das CSV-Dataset durchläuft dieselbe Logik (Chart-/Signal-/Price-Rows).
- **`app.py`**: Sidebar „Dataset mode" (Synthetic | Local CSV upload);
  `st.file_uploader(type=["csv"])`, Inhalt **nur in-memory**
  (`getvalue().decode("utf-8")`), Fehler via `st.error`, **keine** Speicherung,
  **keine** Pfadeingabe. Lazy-Import bleibt; App ohne Streamlit importierbar.
- **Tests:** `tests/test_visual_preview_csv_parser.py` (16) +
  `tests/test_visual_preview_csv_app.py` (5; u. a. kein
  `open(`/`write(`/`write_text`/`write_bytes`/`to_csv`, statischer Pfad-Scan).
  Bestehende Tests grün.
- **pytest: 399 passed** (lokale `.venv`); `app` ohne Streamlit importierbar.

`src/`, CLI, Runner, RiskEngine, Strategien, `pyproject.toml` unverändert.
Keine Echtdaten, keine CSV im Repo, kein Push.

---

*Research-/Backtesting-Kontext. Keine Live-/Paper-Trading-Funktion, keine
Exchange-Anbindung, keine Profitabilitätsaussage, keine Handelsempfehlung.*
