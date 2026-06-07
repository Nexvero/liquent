# LQ-046 — Data-Source / CSV-Loader Hardening Docs + Regression Coverage

## Status

* Phase 2 implemented / finalized.
* DataSource / CSV-loader contract documented; regression coverage added.
* 4 ergänzende Behavior-Locks (`tests/test_data_source_loader_hardening.py`).
* Hohe Bestandsabdeckung (~37 Loader-Tests) war bereits vorhanden — daher
  bewusst kleiner Testumfang.
* Bestehende Loader-/Backtesting-Tests und alle Fixtures unverändert; nur lokale
  Fixtures (lesend) und `tmp_path`.
* Reine Dokumentations-/Regressionsphase.
* Beschreibt den **aktuellen** Data-Source-/CSV-Loader-Stand, kein Wunschdesign.
* No data source changes (`src/liquent/data/sources.py`).
* No new data sources, no new/changed fixtures.
* No external downloads, no real market data, no network calls.
* No exit_reason.
* No Stop-Exit.
* No Runner-Lifecycle change.
* No ranking / evaluation / recommendation logic.
* No Streamlit start.
* No dependency install.
* No live trading.
* No trading recommendation.
* No profitability assessment.

## 1. Purpose

* Den bestehenden Data-Source-/CSV-Loader-Contract aus dem Code und den Tests
  dokumentieren (`src/liquent/data/sources.py`, `tests/fixtures/ohlcv_*.csv`).
* Ergänzende Regressionstests **nur** für die identifizierten Lücken vorbereiten
  (`tests/test_data_source_loader_hardening.py`) — bestehende Fixtures (lesend)
  und `tmp_path`-CSVs für Negativfälle.
* Keine Produktionslogik ändern.
* Diese Doku ist rein deskriptiv: keine Bewertung, kein Ranking, keine
  Empfehlung, keine Profitabilitätsaussage.

## 2. Verified Current Model

Verifiziert lesend gegen den echten Code und die bestehenden Tests
(ohne Änderung).

### DataSource Protocol Contract

`DataSource` (runtime-checkable `Protocol`, nur lesend): `market_data()` und
`order_book_snapshots()`, beide in aufsteigender UTC-Zeit.

### HistoricalFileSource Contract

Datei-basierte lokale OHLCV-CSV-Quelle (nur Standardbibliothek; **kein**
Netzwerk, **keine** Exchange-Anbindung, **keine** Zugangsdaten). `market_data()`
ist eager (Validierungsfehler treten sofort auf) und deterministisch (sortiert
erzwungen). Konstruktor-Parameter: `path`, `timeframe=None`,
`gap_policy="reject"`, `max_gaps=0`, `metadata=None`, `history_policy="flag"`;
ungültige `gap_policy`/`history_policy`/`timeframe` → `ValueError` bei
Konstruktion.

### CSV Schema Contract

Pflicht-Kopfzeile (Spaltenreihenfolge egal):
`timestamp, open, high, low, close, volume`. Abbildung auf das Domänenmodell:
`close` wird Referenzpreis (`bid = ask = close` ⇒ `mid = close`);
`open/high/low` werden validiert, aber nicht gespeichert; `volume` übernommen.

### Validation Contract

Fail-safe `ValueError` mit Zeilenbezug bei:

* fehlender Pflichtspalte,
* leerem **oder** unparsebarem ISO-8601-`timestamp` (`fromisoformat`),
* nicht-numerischem OHLCV-Feld,
* negativem Preis (`open/high/low/close`) oder `volume`,
* `high < low`,
* `open`/`close` außerhalb `[low, high]`,
* nicht strikt aufsteigenden Zeitstempeln (Duplikate, Unsortierung).

### Empty-Data Contract

Vollständig leere Datei (keine Kopfzeile) **oder** Datei nur mit Kopfzeile →
leere Liste (kein Fehler). Fehlende Pflichtspalte bei vorhandener Kopfzeile →
Fehler.

### Gap-Detection Contract

Nur bei gesetztem `timeframe` (sonst deaktiviert, vollständig
rückwärtskompatibel). `gap_policy`:

* `reject` (Default): wirft bei der ersten Lücke,
* `flag`: lädt; Lücken über `gap_report()` (Tupel von `Gap`),
* `tolerate`: lädt, solange Anzahl Lücken `max_gaps` nicht überschreitet, sonst
  `ValueError`.

`Gap` (immutable): `previous_timestamp`, `current_timestamp`,
`expected_delta_seconds`, `actual_delta_seconds`, `missing_bars`
(`actual // expected - 1`, mind. 0). `self.gaps` wird bei **jedem**
`market_data()`-Aufruf zurückgesetzt (kein Akkumulieren über Läufe).

### History-Policy Contract

Nur bei gesetztem `timeframe`. `history_policy`:

* `flag` (Default): markiert (`HistoryReport`), wirft nicht,
* `reject`: wirft bei zu kurzer Historie (`actual_bars < required_bars`),
* `ignore`: kein Report (`history_report()` → `None`).

`HistoryReport` (immutable): `timeframe`, `actual_bars`, `required_bars`
(`required_days * 86400 / timeframe_seconds`), `required_days`, `meets_minimum`
(`actual_bars >= required_bars`), `policy`. `required_days`: 1m→14, 5m→30,
15m→90, 1h→180.

### Metadata Contract

`DataSourceMetadata` (immutable, rein dokumentarisch, defensive Defaults). Ohne
übergebene Metadaten werden Default-Metadaten erzeugt (`source_type=local_csv`,
`source_path`=Pfad, `timeframe`=Loader-Timeframe). Übergebene Metadaten werden
defensiv vervollständigt: `source_path` wird gefüllt, wenn leer; `timeframe`
wird gefüllt, wenn `None`/`""`; andere Felder bleiben unverändert.

### OrderBook NotImplemented Contract

`order_book_snapshots()` wirft bewusst `NotImplementedError` (OHLCV-CSV deckt nur
`MarketData` ab; Orderbuch-Quellen folgen separat).

### Fixture Catalog

Lokale, synthetische CSV-Fixtures unter `tests/fixtures/` (unverändert):

| Fixture | Repräsentiert |
|---|---|
| `ohlcv_valid.csv` | gültige Minimaldaten |
| `ohlcv_no_gap_5m.csv` / `ohlcv_no_gap_1h.csv` | lückenfreie Raster (5m/1h) |
| `ohlcv_gap_5m.csv` | Lücke im 5m-Raster |
| `ohlcv_gap_non_multiple.csv` | Lücke, kein exaktes Vielfaches |
| `ohlcv_empty.csv` | leere Datei |
| `ohlcv_empty_timestamp.csv` | leerer Zeitstempel |
| `ohlcv_missing_column.csv` | fehlende Pflichtspalte |
| `ohlcv_unsorted.csv` / `ohlcv_duplicate_timestamp.csv` | unsortiert / doppelter Zeitstempel |
| `ohlcv_invalid_price.csv` / `ohlcv_negative_volume.csv` | negativer Preis / negatives Volumen |
| `ohlcv_high_lt_low.csv` | `high < low` |
| `ohlcv_open_out_of_range.csv` / `ohlcv_close_out_of_range.csv` | `open`/`close` außerhalb `[low, high]` |

### Determinism / Local-only Invariants

* `market_data()` ist deterministisch (sortiert erzwungen, keine Wanduhr, kein
  Zufall) — gleicher Datei-Inhalt ergibt dieselbe Bar-Liste.
* `Gap`/`HistoryReport` sind rein aus Datei-Inhalt + Konfiguration abgeleitet.
* Ausschließlich lokales Dateilesen; keine Netzwerk-/Download-Pfade.

### Safety / Synthetic-only Invariants

* Nur lokale Fixtures (lesend) bzw. `tmp_path`-CSVs für Negativfälle.
* Keine echten Marktdaten; keine neu committeten CSV-/Bild-/Report-Artefakte;
  bestehende Fixtures bleiben unverändert.
* Ausdrücklich (jede Garantie ungetrennt):
  * keine neuen Datenquellen
  * keine neuen oder geänderten Fixtures
  * keine echten Marktdaten
  * keine externen Downloads
  * keine API-/Exchange-Anbindung
  * kein Paper-Trading
  * kein Live-Trading
  * keine Profitabilitätsbewertung
  * keine Trading-Empfehlung
  * keine Ranking-/Bewertungslogik
  * nur lokale Fixtures und tmp_path
  * keine Produktionslogik geändert

## 3. Edge-Case Table

| Eingang | Ergebnis (aktuell) |
|---|---|
| unbekannte `gap_policy` / `timeframe` / `history_policy` | `ValueError` (Konstruktion) |
| leerer `timestamp` | `ValueError` |
| nicht-leerer, unparsebarer `timestamp` | `ValueError` |
| nicht-numerisches OHLCV-Feld | `ValueError` |
| leere Datei / nur Kopfzeile | leere Liste |
| fehlende Pflichtspalte | `ValueError` |
| `order_book_snapshots()` | `NotImplementedError` |
| `gap_report()` vor `market_data()` | `()` |
| `history_report()` vor `market_data()` | `None` |
| erneuter `market_data()`-Aufruf | Gaps werden zurückgesetzt (kein Akkumulieren) |
| übergebene Metadaten mit leerem `source_path` | Pfad wird ergänzt |

## 4. Regression Invariants

* Validierung ist fail-safe (`ValueError` mit Zeilenbezug), kein stilles
  Durchlassen fehlerhafter Daten.
* Leere/header-only Dateien sind stabil (leere Liste).
* Reporter-Zustand (`gaps`/`history_report`) ist je `market_data()`-Aufruf
  deterministisch und wird zurückgesetzt.
* Reines, lokales Dateilesen; keine Artefakte, keine echten Marktdaten.

## 5. Safety Boundaries

* No API keys.
* No exchange credentials.
* No network calls by Liquent.
* No external data download by Liquent.
* No live data source.
* No orders.
* No paper-trading connection.
* Nur lokale Fixtures / `tmp_path`; keine neu committeten CSV/Screenshots/Reports.
* No profitability assessment.
* No trading recommendation.
* No ranking / evaluation language.

## 6. README/Roadmap Impact

README:

* optional kein Link in Phase 1,
* Phase 2 kann den LQ-046-Link ergänzen.

Roadmap:

* LQ-046 als Data-Source-/CSV-Loader-Hardening-/Regression-Track ergänzen
  (Phase 2).
* Status:
  * data-source / CSV-loader contract documented,
  * additional regression coverage added,
  * no production logic changes,
  * Runner Lifecycle bleibt gemäß LQ-040 pausiert.

Visual Preview Index:

* nicht erweitern,
* LQ-046 ist kein Visual-Preview-Track.

## 7. Phase Plan

* **Phase 1** (abgeschlossen): Doku-Entwurf + Lückenabgleich gegen die
  bestehenden Loader-Tests; Entwurf von
  `tests/test_data_source_loader_hardening.py`. Kein Commit.
* **Phase 2** (diese): Doku finalisiert, Tests finalisiert, Doku-/Link-Test
  (`tests/test_data_source_loader_hardening_doc.py`), README/Roadmap minimal
  verlinkt, Teststand aktualisiert. Kein Commit.
* **Phase 3**: Commit der erwarteten Dateien. Kein Push ohne separate Freigabe.

## 7a. Implementation Status (Phase 2)

* DataSource / CSV-loader contract documented (Verified Current Model, Schema/
  Validation/Empty-Data/Gap-Detection/History-Policy/Metadata/OrderBook
  Contracts, Fixture Catalog, Edge-Case Table).
* 4 ergänzende Behavior-Locks hinzugefügt
  (`tests/test_data_source_loader_hardening.py`) — Negativfälle nur über
  `tmp_path`; hohe Bestandsabdeckung war bereits vorhanden, daher bewusst kleiner
  Testumfang.
* Abgesichert: malformed (nicht-leerer, unparsebarer) ISO-Timestamp →
  `ValueError`; nicht-numerisches OHLCV-Feld → `ValueError`; Reporter-
  Initialzustand (`gap_report() == ()`, `history_report() is None`);
  Gap-State-Reset bei erneutem `market_data()`.
* `unknown history_policy` war bereits abgedeckt
  (`test_unknown_history_policy_rejected`) und wurde **nicht** dupliziert.
* Metadata-Vervollständigung (source_path/timeframe) war bereits abgedeckt und
  wurde **nicht** dupliziert.
* Exakte `meets_minimum`-Grenze (required_bars 5m = 8640 Bars) bewusst **nicht**
  getestet (zu große Testdaten).
* `src/liquent/data/sources.py` unverändert (keine Produktionslogik).
* Bestehende Loader-/Backtesting-Tests unverändert; alle Fixtures unverändert;
  keine neuen CSVs oder Artefakte; bestehende Fixtures nur lesend.
* README-Link + Teststand aktualisiert.
* Roadmap-Link + Status aktualisiert.
* Doku-/Link-Test hinzugefügt: 12 Tests
  (`tests/test_data_source_loader_hardening_doc.py`).
* Visual Preview Index unverändert.
* No exit_reason, no Stop-Exit, no new data source, no new/changed fixtures.
* No dependency installed, no Streamlit start, no real market data, no external
  download, no artefacts.
* pytest result: siehe README / Roadmap (aktueller verifizierter Teststand).

## 8. Test Plan

Ergänzende Behavior-Locks in `tests/test_data_source_loader_hardening.py` —
ausschließlich **bestehendes** Verhalten; bestehende Fixtures (lesend) +
`tmp_path`-CSVs für Negativfälle. Keine neuen committeten Fixtures/Artefakte.

Adoptierte Lücken (echtes, bisher nicht explizit gesichertes Verhalten):

* **validation** — nicht-leerer, unparsebarer ISO-`timestamp` → `ValueError`
  (`tmp_path`; bisher nur leerer Timestamp getestet).
* **validation** — nicht-numerisches OHLCV-Feld (z. B. `open="abc"`) →
  `ValueError` (`tmp_path`).
* **state** — Reporter-Initialzustand vor dem ersten `market_data()`:
  `gap_report() == ()` und `history_report() is None`.
* **state** — erneuter `market_data()`-Aufruf akkumuliert keine Gaps
  (State-Reset von `self.gaps`).

Bewusst **nicht** übernommen (bereits abgedeckt):

* valid load, Float-Parsing, alle OHLCV-Reject-Fälle (negativ/Spannen),
  header-only/empty, missing column, leerer Timestamp.
* order_book NotImplemented; timeframe None/5m/1h; unknown timeframe/gap_policy/
  **history_policy** (test_unknown_history_policy_rejected).
* gap reject/flag/tolerate, missing_bars, non_multiple, empty-with-timeframe.
* Default-Metadaten **und** Metadaten-Vervollständigung (source_path/timeframe).
* history flag/reject/ignore/no-timeframe/empty, required_bars 5m/1h.

Bewusst **nicht** als Test erzwungen (zu große Testdaten nötig):

* exakte `meets_minimum`-Grenze (required_bars 5m = 8640 Bars).

## 9. Non-Goals

* keine Änderung an `src/liquent/data/sources.py` (Loader-Produktionslogik),
* keine neuen Datenquellen, keine neuen/geänderten Fixtures,
* keine Änderung an bestehenden Loader-/Backtesting-Tests,
* kein `exit_reason`, keine Stop-Exit-Logik, keine Runner-Lifecycle-Änderung,
* keine RiskEngine-/CostModel-/Metrics-/Reporting-/Comparison-/CLI-/Strategie-
  Änderung,
* keine Ranking-/Bewertungslogik,
* keine echten Marktdaten, keine externen Downloads, keine API-/Exchange-/Live-/
  Paper-Anbindung,
* keine neu committeten CSV-/Bild-/Report-Artefakte,
* keine Profitabilitätsbewertung, keine Trading-Empfehlung.

## 10. Deferred Topics

1. Weitere Datenquellen (Exchange-API, Orderbuch-Snapshots) bleiben außerhalb
   dieses Tracks (aktuell `NotImplementedError`).
2. Zusätzliche Timeframes über die v1-Werte hinaus bleiben offen.
3. Eine exakte `meets_minimum`-Grenzwert-Prüfung erfordert große Testdaten und
   ist bewusst verschoben.
4. Streaming-/inkrementelles Laden (statt eager) bleibt ein separater,
   ausdrücklich freizugebender Track.
