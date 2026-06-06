# LQ-023 — Visual Preview CSV Validation UX and Sample Template

> Status: **Phase 1 — Spezifikation / Dokumentation.** Keine Implementierung,
> keine Dependency-Installation, keine `tools/`-Änderung, keine Echtdaten, keine
> CSV im Repo. Plant eine nutzerfreundlichere CSV-UX (Format-Hinweise, Sample-
> Template, klarere Validierungsfehler) für den lokalen Upload aus LQ-022. Rein
> technisch — keine Profitabilitätsbewertung, keine Trading-Empfehlung.

## 1. Ausgangslage

- LQ-022 hat lokalen CSV-Upload in der Visual Preview eingeführt
  (`build_dataset_from_csv_text` in `tools/visual_preview/preview_logic.py`,
  `file_uploader` in `app.py`).
- CSVs werden **nur in-memory** verarbeitet; Pflichtspalten `timestamp,bid,ask`;
  `volume` optional (Default `1.0`); naive Timestamps abgelehnt; Tests für
  Parser, App-Safety und Upload-Pfad vorhanden.
- Die Funktion ist technisch da, die **UX** kann klarer werden: erwartetes Format
  vor Upload sichtbar; verständlichere, feldbezogene Parserfehler; kopierbares
  Beispiel-CSV.

### Verifizierte Befunde (bindend für Phase 2)

- **Aktuelle Parser-Meldungen sind deutsch und ohne Zeilennummer** (z. B.
  „CSV fehlen Pflichtspalten: …", „timestamp muss timezone-aware sein (UTC): …",
  „bid muss > 0 sein (war …)").
- **Die Parse-Schleife nutzt `for row in reader` ohne `enumerate`** → derzeit
  **kein** Row-Tracking. Phase 2 muss Zeilen zählen (Header = CSV-Zeile 1, erste
  Datenzeile = CSV-Zeile 2) und die Row-Nummer in die Helfer
  (`_parse_csv_timestamp`/`_parse_csv_float`) einfädeln.
- `SAMPLE_CSV_TEMPLATE` / `CSV_REQUIRED_COLUMNS` existieren noch **nicht** als
  Konstanten (`_CSV_REQUIRED_COLUMNS` ist privat).

CSV-Upload bleibt lokal/in-memory — keine Echtdaten, keine Speicherung, keine
Trading-Entscheidung, keine Profitabilitätsbewertung.

## 2. Ziel

Bessere CSV-UX in der Visual Preview:
- Format-Hinweis direkt im CSV-Modus,
- **kopierbares** Beispiel-CSV (Codeblock),
- klarere, neutrale, **feldbezogene** Validierungsfehler mit **Zeilennummer**,
- Fehlermeldungen führen den Nutzer zur Korrektur,
- **keine** echten CSV-Dateien im Repo, **keine** Datei-Templates als Artefakte,
  **kein** externer Download.

## 3. Nicht-Ziele

keine Echtdaten · keine echten CSV im Repo · kein automatischer Download · keine
API-/Exchange-Anbindung · kein Broker · kein Paper-Trading · kein Live-Trading ·
keine Orders · keine Persistenz von Uploads · keine Reportdateien · kein
Deployment · kein Login/Auth · keine Optimierung/Parameter-Suche · keine
Profitabilitätsbewertung · keine Trading-Empfehlung · keine Runner-Integration ·
keine Änderung an Strategie-/Runner-/RiskEngine-Kernlogik · **keine neue
Dependency**.

## 4. CSV-Format-Hinweise in der UI (CSV-Modus)

- **Pflichtspalten:** `timestamp`, `bid`, `ask`. **Optional:** `volume`.
- `timestamp` muss **ISO-8601 und timezone-aware** sein
  (Beispiel `2026-01-01T00:00:00+00:00`).
- `bid`/`ask` positiv-numerisch; `ask >= bid`.
- `volume` optional; fehlt/leer → Default `1.0`.
- Zeilen werden nach `timestamp` sortiert.
- Hinweistext: **„CSV upload is local/in-memory only. Files are not saved by
  Liquent."**

## 5. Sample CSV Template

```csv
timestamp,bid,ask,volume
2026-01-01T00:00:00+00:00,100.0,100.5,1.0
2026-01-01T00:05:00+00:00,100.2,100.7,1.0
2026-01-01T00:10:00+00:00,100.4,100.9,1.0
```

- Template als **String-Konstante** `SAMPLE_CSV_TEMPLATE` in `preview_logic.py`
  (testbar, Streamlit-frei). **Kein** echtes `.csv`-File im Repo.
- Anzeige via `st.code(SAMPLE_CSV_TEMPLATE, language="csv")`.

### Bewertung Download-Button

- **Option A — nur kopierbarer Codeblock (`st.code`):** minimal, keine
  Datei-Artefakte; Nutzer kopiert manuell.
- **Option B — `st.download_button` für statisches Template:** bessere UX, erzeugt
  keine Repo-Datei (nur lokale Browser-Aktion); aber „Download" missverständlich
  und erfordert klare Sicherheitsformulierung (kein externer Download, nur
  statisches Template).

> **Empfehlung: Option A** in Phase 2 (nur `st.code`, **kein** `download_button`).

## 6. Validierungsfehler-UX

Klarere, englische, feldbezogene Meldungen **mit CSV-Zeilennummer** (Header = Zeile
1). Beispiele:

- Empty CSV: „CSV is empty. Expected columns: timestamp,bid,ask."
- Missing column: „CSV is missing required column: bid."
- Invalid timestamp: „Row 3: timestamp is not a valid ISO-8601 datetime."
- Naive timestamp: „Row 3: timestamp must include timezone information,
  e.g. +00:00."
- Invalid bid: „Row 3: bid must be a positive number."
- Invalid ask: „Row 3: ask must be a positive number."
- ask < bid: „Row 3: ask must be greater than or equal to bid."
- Invalid volume: „Row 3: volume must be numeric when provided."

> **Keine** technischen Tracebacks in der UI. Der Parser wirft `ValueError`; die
> App zeigt `st.error(str(error))`. **Zeilennummer = CSV-Zeile inkl. Header als
> Zeile 1** (Datenzeile 1 = CSV-Zeile 2) — Entscheidung dokumentiert (§12.2).

## 7. Parser-/App-Änderungen Phase 2

**`preview_logic.py`:**
- `SAMPLE_CSV_TEMPLATE: str`, öffentliches `CSV_REQUIRED_COLUMNS: tuple[str, ...]`,
- optional `get_csv_format_help() -> dict[str, Any]` (Regeln als Datenstruktur),
- **Row-Nummern** in alle Validierungsfehler (Helfer um `row: int`-Parameter
  erweitern; Schleife mit `enumerate(reader, start=2)`),
- englische, nutzerführende Meldungen (gemäß §6).

**`app.py` (CSV-Modus):**
- `st.markdown`/`st.caption` mit Formatregeln + Safety-Hinweis,
- `st.code(SAMPLE_CSV_TEMPLATE, language="csv")`,
- bei Uploadfehler `st.error(str(error))`; **keine** Datei speichern.

> `preview_logic.py` bleibt Streamlit-frei; `app.py` bleibt **ohne** Streamlit
> importierbar; **keine** neue Dependency; **kein** File-I/O.

## 8. Tests für Phase 2

**Parser/UX:**
1. `SAMPLE_CSV_TEMPLATE` ist parsebar (`build_dataset_from_csv_text`).
2. `SAMPLE_CSV_TEMPLATE` erzeugt ≥ 3 Bars.
3. fehlende Pflichtspalte nennt die **konkrete** Spalte.
4. ungültiger timestamp enthält **Row-Hinweis** (z. B. „Row 3").
5. naive timestamp enthält Hinweis auf **timezone**.
6. ungültiger bid enthält „positive number".
7. `ask < bid` enthält „greater than or equal".
8. ungültige volume enthält „numeric".
9. Fehlermeldungen enthalten **keine** Traceback-Details.

**App/static:**
10. `app.py` enthält/zeigt `SAMPLE_CSV_TEMPLATE`.
11. `app.py` nutzt `st.code` (o. ä.) für das CSV-Beispiel.
12. `app.py` nutzt weiterhin `file_uploader`.
13. **kein** `download_button` in Phase 2 (Empfehlung A).
14. keine Datei-Schreibpfade (`open(`/`write(`/`write_text`/`write_bytes`/
    `to_csv`).
15. keine Netzwerk-/API-/Exchange-/Paper-/Live-Pfade (statischer Scan).
16. Import **ohne** Streamlit bleibt grün.
17. bestehende Tests bleiben grün.

**README/Doku (optional):**
18. README enthält CSV-Format + Safety-Hinweis.

## 9. README/Doku-Auswirkung

README „Visual Preview" um **CSV Format Requirements** + Beispiel-CSV ergänzen,
mit Hinweisen: Upload local/in-memory only; Liquent does not save uploaded CSV
files; no live trading; no trading recommendation; no profitability assessment.
Keine echten CSV-Dateien, keine Ergebnisinterpretation. Teststand nach Phase 2
aktualisieren.

## 10. Sicherheitsgrenzen

keine API-Keys · keine Exchange-Credentials · keine Netzwerk-Calls · kein
externer Download · keine Live-Datenquelle · keine Orders · keine Paper-Trading-
Verbindung · **keine Speicherung hochgeladener CSVs** · **keine CSV-Beispieldatei
als Artefakt** · keine Reportdateien · keine Profitabilitätsbewertung · keine
Empfehlungssprache · keine Equity-/Performance-Darstellung.

## 11. Kompatibilität

- Bestehender Parser bleibt kompatibel (gleiche Validierungsregeln; nur Meldungen
  + Row-Nummern verbessert). **Hinweis:** Tests, die auf den **bisherigen
  deutschen** Meldungstext prüfen, gibt es nicht (Bestandstests nutzen
  `_expect_value_error`/`pytest.raises` ohne Textabgleich) — die Umstellung auf
  englische Meldungen ist daher unkritisch (in Phase 2 verifizieren).
- Synthetische Datasets unverändert; `preview_logic.py` Streamlit-frei; `app.py`
  ohne Streamlit importierbar; **keine** neue Pflicht-Dependency; **keine**
  `src/`-Änderung; keine Änderung an Strategien/Runner/RiskEngine/CLI.

## 12. Offene Entscheidungspunkte

1. **Codeblock oder Download-Button?** → *Empfehlung: Codeblock*, kein
   `download_button` in Phase 2.
2. **Row-Nummer: Datenzeile oder CSV-Zeile?** → *Empfehlung: CSV-Zeile inkl.
   Header* (Header = Zeile 1, erste Datenzeile = Zeile 2).
3. **Mehrere Timestamp-Formate?** → *Empfehlung: nur ISO-8601*, keine zusätzliche
   Format-Magie.
4. **OHLCV-CSV unterstützen?** → *Empfehlung: nein*, später separat; Phase 2
   bleibt bid/ask.
5. **Sample-CSV als echte Datei committen?** → *Empfehlung: nein* (String-
   Konstante).

---

## Phase 2 Implementation Status

Umgesetzt (Tools/UI/Doku — keine `src/`-/`pyproject`-Änderung, keine neue Dependency):

- **`preview_logic.py`**: öffentliche Konstanten `SAMPLE_CSV_TEMPLATE`,
  `CSV_REQUIRED_COLUMNS = ("timestamp","bid","ask")`, `CSV_OPTIONAL_COLUMNS =
  ("volume",)`. Sample ist ein **String** (kein `.csv`-File), vom Parser
  erfolgreich parsebar (3 Bars).
- **Row-nummerierte, englische Fehlermeldungen** (CSV-Zeile inkl. Header = Zeile 1;
  `enumerate(reader, start=2)`): „CSV is empty…", „CSV is missing required
  column: …", „CSV contains no data rows.", „CSV row N: timestamp is not a valid
  ISO-8601 datetime.", „… must include timezone information, e.g. +00:00.",
  „… bid/ask must be a positive number.", „… ask must be greater than or equal to
  bid.", „… volume must be numeric when provided." — **keine** Tracebacks; die
  Validierungsregeln sind **unverändert** (nicht gelockert).
- **`app.py`** (CSV-Modus): Format-Hinweis (`st.markdown`) + kopierbares Beispiel
  `st.code(SAMPLE_CSV_TEMPLATE, language="csv")`; **kein** `download_button`,
  **kein** File-I/O, keine Speicherung. Lazy-Import bleibt; App ohne Streamlit
  importierbar.
- **README**: „CSV format requirements" (Required/Optional, tz-aware, positive,
  `ask >= bid`, Default 1.0, local/in-memory only, not saved, row-numbered error).
- **Tests:** `test_visual_preview_csv_parser.py` (+9: Sample parsebar/≥3 Bars,
  Required-Columns-Konstante, konkrete Spaltennennung, Row-/timezone-/positive-/
  „greater than or equal"-/„numeric"-Meldungen, keine Tracebacks) und
  `test_visual_preview_csv_app.py` (+2: `st.code`/`SAMPLE_CSV_TEMPLATE`, kein
  `download_button`). Bestehende Tests grün.
- **pytest: 410 passed** (lokale `.venv`); `app` ohne Streamlit importierbar.

`src/`, CLI, Runner, RiskEngine, Strategien, `pyproject.toml` unverändert. Keine
Echtdaten, keine CSV im Repo, kein Push.

---

*Research-/Backtesting-Kontext. Keine Live-/Paper-Trading-Funktion, keine
Exchange-Anbindung, keine Profitabilitätsaussage, keine Handelsempfehlung.*
