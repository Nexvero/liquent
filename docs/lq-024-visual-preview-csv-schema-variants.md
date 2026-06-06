# LQ-024 — Visual Preview CSV Schema Variants / OHLCV Mapping

> Status: **Phase 1 — Spezifikation / Dokumentation.** Keine Implementierung,
> keine Dependency-Installation, keine `tools/`-/`src/`-Änderung, keine Echtdaten,
> keine CSV im Repo. Plant, wie die Visual Preview **zusätzlich** zum bestehenden
> bid/ask-CSV-Format auch ein **OHLCV-CSV-Format** akzeptiert. Rein technisch —
> keine Profitabilitätsbewertung, keine Trading-Empfehlung.

## 1. Ausgangslage

- LQ-022 hat den lokalen CSV-Upload (bid/ask-Schema) eingeführt; LQ-023 hat die
  Validierungs-UX (Row-nummerierte Fehler, Sample-Template) ergänzt.
- Der Preview-Parser akzeptiert aktuell **nur** das **bid/ask-Schema**.
- Viele lokale OHLCV-Exporte liegen jedoch im **OHLCV-Format** vor — das die
  Kernbibliothek bereits anderswo verwendet.

### Verifizierte Befunde (bindend für Phase 2)

- **Preview-Parser (`tools/visual_preview/preview_logic.py`):**
  `CSV_REQUIRED_COLUMNS = ("timestamp", "bid", "ask")`, optional `volume`
  (Default `1.0`); `build_dataset_from_csv_text` baut `MarketData` direkt aus
  `bid`/`ask`; `mid = (bid + ask) / 2`.
- **Kern-`src/liquent/data/HistoricalFileSource`:** nutzt das **OHLCV-Schema**
  `_REQUIRED_COLUMNS = ("timestamp","open","high","low","close","volume")`,
  validiert `low <= open <= high` und `low <= close <= high`, Preise/`volume`
  nicht negativ, und mappt **`close → bid = ask = close`** ⇒ `mid = close`
  (Close-to-Close-Referenz).
- Damit existiert ein **etabliertes, konsistentes OHLCV→bid/ask-Mapping**
  (`close→bid=ask=close`), das die Preview übernehmen kann — **ohne** `src/`
  anzufassen (das Mapping wird im Preview-Parser nachgebildet).

OHLCV-Upload bleibt lokal/in-memory — keine Echtdaten, keine Speicherung, keine
Trading-Entscheidung, keine Profitabilitätsbewertung.

## 2. Ziel

Die Preview soll **zwei** lokale CSV-Schemata akzeptieren:
- **bid/ask** (bestehend, Default-Pfad, unverändert), und
- **OHLCV** (neu): `timestamp,open,high,low,close,volume` → intern auf
  `bid = ask = close` (⇒ `mid = close`) abgebildet, konsistent zur
  Kernbibliothek.

Beide Schemata münden in dieselbe `PreviewDataset`-/Preview-Logik (Technical
Summary, Chart, Signal Table). **Automatische Schema-Erkennung** anhand der
CSV-Kopfzeile.

## 3. Nicht-Ziele

keine Echtdaten · keine echte CSV im Repo · kein Download · keine API-/Exchange-
Anbindung · kein Broker · kein Paper-/Live-Trading · keine Orders · keine
Persistenz von Uploads · keine Reportdateien · kein Deployment · kein Login/Auth ·
keine Optimierung/Parameter-Suche · keine Profitabilitätsbewertung · keine
Trading-Empfehlung · keine Runner-Integration · **keine `src/`-Änderung** (das
OHLCV-Mapping wird im Preview-Parser nachgebildet, nicht aus `HistoricalFileSource`
importiert) · **keine neue Dependency** · kein pandas.

## 4. Schema-Erkennung (header-basiert)

Anhand der CSV-Kopfzeile (`reader.fieldnames`), **bevor** Datenzeilen gelesen
werden:

1. Enthält der Header **`bid` und `ask`** → **bid/ask-Schema** (bestehender Pfad).
2. Sonst, enthält der Header **`open,high,low,close`** → **OHLCV-Schema**.
3. Sonst → klarer Fehler:
   „CSV header not recognized. Expected either `timestamp,bid,ask[,volume]` or
   `timestamp,open,high,low,close,volume`."

> Reihenfolge wichtig: bid/ask hat Vorrang (Default-Schema, rückwärtskompatibel).
> Mischheader (sowohl `bid/ask` als auch OHLCV) → als bid/ask behandeln und das
> dokumentieren (Entscheidungspunkt §11.3).

## 5. OHLCV → bid/ask-Mapping + Validierung

Pro Datenzeile im OHLCV-Schema:
- Pflichtspalten: `timestamp,open,high,low,close,volume` (volume hier **Pflicht**
  wie im Kernschema — oder optional mit Default `1.0`? siehe §11.4).
- `timestamp`: ISO-8601, **timezone-aware** (naiv → Fehler; identisch zu
  bid/ask).
- `open/high/low/close/volume`: numerisch; Preise/`volume` **nicht negativ**.
- **Konsistenzprüfung** (analog Kern): `low <= open <= high`,
  `low <= close <= high`; `close > 0`.
- **Mapping:** `bid = ask = close` ⇒ `mid = close`.
- Sortierung stabil nach `timestamp`; Fehler **row-nummeriert** (CSV-Zeile inkl.
  Header = Zeile 1), englisch, kein Traceback — exakt wie bei bid/ask.

Beispiel-Fehlermeldungen:
- „CSV row 3: high must be greater than or equal to low."
- „CSV row 3: close must be within [low, high]."
- „CSV row 3: close must be a positive number."

## 6. Parser-/App-Änderungen Phase 2

**`preview_logic.py`** (Streamlit-frei, stdlib `csv`, kein File-I/O, kein
pandas):
- `CSV_OHLCV_REQUIRED_COLUMNS: tuple[str, ...] = ("timestamp","open","high","low","close","volume")`
- `SAMPLE_OHLCV_CSV_TEMPLATE: str` (String-Konstante, **kein** `.csv`-File),
- interne Aufteilung: `_detect_csv_schema(fieldnames) -> str` (`"bid_ask"` |
  `"ohlcv"`), plus `_build_dataset_from_ohlcv_rows(...)`,
- **`build_dataset_from_csv_text` bleibt der öffentliche Einstieg** und wählt nach
  Schema-Erkennung den passenden Pfad (bid/ask **byte-identisch** wie heute).

**`app.py`** (CSV-Modus): Format-Hinweis um **beide** Schemata erweitern; beide
Sample-Templates via `st.code` anzeigen; weiterhin `file_uploader`, **kein**
`download_button`, **kein** File-I/O, keine Speicherung. Lazy-Import bleibt.

## 7. Tests für Phase 2 (ohne Streamlit-E2E, CSV als String)

1. OHLCV-CSV → `PreviewDataset` mit `bid == ask == close` und `mid == close`.
2. `SAMPLE_OHLCV_CSV_TEMPLATE` ist parsebar (≥ 3 Bars).
3. bid/ask-Schema bleibt **unverändert** (Regressionsanker; gleiche Ergebnisse
   wie LQ-022/023).
4. Schema-Erkennung: bid/ask-Header → bid/ask; OHLCV-Header → OHLCV.
5. unbekannter Header → klarer „header not recognized"-Fehler.
6. OHLCV-Validierung: `high < low` abgelehnt (row-nummeriert).
7. OHLCV-Validierung: `close` außerhalb `[low, high]` abgelehnt.
8. OHLCV-Validierung: negativer/nicht-numerischer Preis abgelehnt.
9. naiver Timestamp (OHLCV) abgelehnt (gleiche Regel).
10. unsortierte OHLCV-CSV → nach `timestamp` sortiert.
11. `generate_preview_summary` funktioniert mit OHLCV-Dataset.
12. keine Profitabilitätsfelder in den Strukturen.
13. `app.py` ohne Streamlit importierbar; kein File-Write; statischer Pfad-Scan.
14. bestehende Tests bleiben grün.

## 8. README/Doku-Auswirkung

README „Visual Preview" um den OHLCV-Modus ergänzen: zweites unterstütztes
Schema + Beispiel; Hinweis `close → bid = ask = close` (⇒ `mid = close`),
konsistent zur Kernbibliothek. Sicherheitsgrenzen unverändert (local/in-memory
only, not saved). Teststand nach Phase 2.

## 9. Sicherheitsgrenzen

keine API-Keys · keine Exchange-Credentials · keine Netzwerk-Calls · kein
Download · keine Live-Datenquelle · keine Orders · keine Paper-Trading-
Verbindung · keine Speicherung hochgeladener CSVs · keine CSV-Beispieldatei als
Artefakt · keine Reportdateien · keine Profitabilitätsbewertung · keine
Empfehlungssprache · keine Equity-/Performance-Darstellung.

## 10. Kompatibilität

- **bid/ask-Schema bleibt Default und byte-identisch** (Regressionsanker).
- `preview_logic.py` bleibt Streamlit-frei; `app.py` ohne Streamlit importierbar.
- **Keine** neue Pflicht-Dependency; **keine** `src/`-Änderung (OHLCV-Mapping wird
  im Preview-Parser nachgebildet — `HistoricalFileSource` wird **nicht**
  importiert, da es ein `DataSource` mit Datei-/Validierungslogik ist, nicht ein
  reiner Text-Parser).
- Keine Änderung an Strategien/Runner/RiskEngine/CLI. Bestehende Tests bleiben
  grün.

## 11. Offene Entscheidungspunkte

1. **OHLCV im Preview-Parser nachbilden oder `HistoricalFileSource` nutzen?**
   → *Empfehlung: nachbilden* (Tools-lokal, Text-Parser; `HistoricalFileSource`
   ist Datei-/`DataSource`-orientiert und würde `src/`-Kopplung erzwingen).
2. **`high == low`-Flatbars erlauben?**
   → *Empfehlung: ja* (`high >= low` zulässig; Konsistenzprüfung nutzt `>=`/`<=`).
3. **Mischheader (bid/ask UND OHLCV)?**
   → *Empfehlung: als bid/ask behandeln* (Default-Vorrang), dokumentiert.
4. **`volume` im OHLCV-Schema Pflicht oder optional?**
   → *Empfehlung: optional mit Default `1.0`* (konsistent zum bid/ask-Schema der
   Preview; das Kernschema verlangt es zwar, die Preview muss aber nicht
   identisch streng sein).
5. **Echte Intrabar-High/Low-Nutzung?**
   → *Empfehlung: nein* — Preview bleibt Mid-/Close-Proxy (`mid = close`); OHLC
   `open/high/low` werden nur validiert, nicht in Signale überführt (wie im Kern).
6. **Separates `--`/Auswahl-Widget statt Auto-Erkennung?**
   → *Empfehlung: Auto-Erkennung per Header* (einfachste UX); optionaler
   manueller Override später.

---

## Phase 2 Implementation Status

Umgesetzt (Tools/UI/Doku — keine `src/`-/`pyproject`-Änderung, keine Dependency):

- **`preview_logic.py`**: Auto-Schema-Erkennung `_detect_csv_schema(fieldnames)`
  (`bid` UND `ask` → `bid_ask`; sonst `open/high/low/close` → `ohlcv`; partielles
  bid/ask → `bid_ask` für konkrete Spaltenmeldung; sonst „header not
  recognized"). OHLCV-Pfad `_parse_ohlcv_rows` mappt **`bid = ask = close`**
  (⇒ `mid = close`) mit Validierung (`high >= low`, `low <= open/close <= high`,
  Preise nicht-negativ, `close > 0`, tz-aware timestamp, row-nummerierte englische
  Fehler). Neue Konstanten `CSV_OHLCV_REQUIRED_COLUMNS`,
  `SAMPLE_OHLCV_CSV_TEMPLATE` (String, kein `.csv`-File). **bid/ask byte-identisch**
  (Regressionsanker grün).
- **`app.py`** (CSV-Modus): Hinweis nennt **beide** Schemata; zeigt **beide**
  Sample-Templates via `st.code`; weiterhin `file_uploader`, **kein**
  `download_button`, **kein** File-I/O. Lazy-Import bleibt; ohne Streamlit
  importierbar.
- **`build_dataset_from_csv_text` bleibt öffentlicher Einstieg** und verzweigt
  nach Schema; `generate_preview_summary` funktioniert mit OHLCV-Dataset.
- **README**: zweites Schema + Beispiel + `close→bid=ask`-Hinweis.
- **Tests:** `test_visual_preview_csv_parser.py` (+11: OHLCV-Mapping, Sample,
  bid/ask-Regression, unbekannter Header, `high<low`, `close` außerhalb
  `[low,high]`, negativ/nicht-numerisch, naiv, Sortierung, Summary, Mischheader-
  Vorrang) und `test_visual_preview_csv_app.py` (OHLCV-Sample). Bestehende Tests
  grün (inkl. angepasster Teil-bid/ask-Erkennung).
- **pytest: 421 passed** (lokale `.venv`); `app` ohne Streamlit importierbar.

`src/`, CLI, Runner, RiskEngine, Strategien, `pyproject.toml` unverändert. Keine
Echtdaten, keine CSV im Repo, kein Push.

---

*Research-/Backtesting-Kontext. Keine Live-/Paper-Trading-Funktion, keine
Exchange-Anbindung, keine Profitabilitätsaussage, keine Handelsempfehlung.*
