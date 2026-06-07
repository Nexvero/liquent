"""Doku-/Link-Tests für die Data-Source-/CSV-Loader-Hardening-Doku (LQ-046 Phase 2).

Prüft die finalisierte Doku + README/Roadmap-Verlinkung, ohne fragil zu sein.
Kein Streamlit, kein Netzwerk, keine echten Daten, keine Codeänderung. Importiert
keine Produktionslogik und erzeugt keine Artefakte.

Hinweis: Die LQ-046-Doku nennt legitim bestehende Fixture-Dateinamen (``*.csv``)
im Fixture-Katalog. Der Artefakt-Check prüft daher das Dateisystem (``docs/``)
auf neu committete Artefakte — NICHT den Doku-Text auf die Zeichenkette ``.csv``.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "lq-046-data-source-csv-loader-hardening.md"
_README = _ROOT / "README.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"
_VP_INDEX = _ROOT / "docs" / "visual-preview-index.md"

_DOC_NAME = "lq-046-data-source-csv-loader-hardening.md"


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


# 1: LQ-046-Doku existiert.
def test_spec_doc_exists():
    assert _DOC.is_file()


# 2: Doku enthält die zentralen Abschnitte.
def test_doc_has_core_sections():
    doc = _doc()
    for heading in (
        "Status",
        "Purpose",
        "Verified Current Model",
        "DataSource Protocol Contract",
        "HistoricalFileSource Contract",
        "CSV Schema Contract",
        "Validation Contract",
        "Empty-Data Contract",
        "Gap-Detection Contract",
        "History-Policy Contract",
        "Metadata Contract",
        "OrderBook NotImplemented Contract",
        "Fixture Catalog",
        "Determinism / Local-only Invariants",
        "Safety / Synthetic-only Invariants",
        "Edge-Case Table",
        "Regression Invariants",
        "Safety Boundaries",
        "Test Plan",
        "Non-Goals",
        "Deferred Topics",
        "Implementation Status",
    ):
        assert heading in doc, f"LQ-046-Doku fehlt Abschnitt: {heading!r}"


# 3: Doku verankert verifizierte echte Identifier (kein erfundenes Feld).
def test_doc_documents_real_identifiers():
    doc = _doc()
    for token in (
        "HistoricalFileSource",
        "DataSourceMetadata",
        "HistoryReport",
        "gap_policy",
        "history_policy",
        "gap_report",
        "history_report",
        "market_data",
    ):
        assert token in doc, f"LQ-046-Doku fehlt verifizierter Bezeichner: {token!r}"


# 4: README verlinkt LQ-046.
def test_readme_links_doc():
    assert _DOC_NAME in _README.read_text(encoding="utf-8")


# 5: Roadmap verlinkt LQ-046.
def test_roadmap_links_doc():
    assert _DOC_NAME in _ROADMAP.read_text(encoding="utf-8")


# 6: Visual Preview Index enthält NICHT LQ-046.
def test_visual_preview_index_has_no_lq046():
    text = _VP_INDEX.read_text(encoding="utf-8").lower()
    assert _DOC_NAME not in text
    assert "lq-046" not in text


# 7: keine verbotene Wertungssprache in der LQ-046-Doku (fragment-gebaute Liste,
# damit diese Testdatei sich nicht selbst matcht). Achtung: die deutsche Vokabel
# "Gewinner" enthielte "winner" — die Doku vermeidet sie bewusst.
def test_no_forbidden_valuation_language():
    doc = _doc().lower()
    forbidden = [
        "win" + "ner",
        "guar" + "anteed",
        "best " + "strategy",
        "should " + "trade",
    ]
    for token in forbidden:
        assert token not in doc, f"verbotener Wertungsbegriff: {token!r}"


# 8: Doku benennt ausdrücklich die Local-only-/No-Production-Garantien.
def test_doc_states_local_only_guarantees():
    doc = " ".join(_doc().lower().split())
    for token in (
        "keine neuen datenquellen",
        "keine echten marktdaten",
        "keine externen downloads",
        "keine profitabilitätsbewertung",
        "keine trading-empfehlung",
    ):
        assert token in doc, f"LQ-046-Doku benennt nicht ausdrücklich: {token!r}"


# 9: Doku benennt ausdrücklich: keine API-/Exchange-Anbindung, kein Paper-/Live-Trading.
def test_doc_states_no_api_paper_live():
    doc = _doc().lower()
    assert "api-/exchange-anbindung" in doc
    assert "kein paper-trading" in doc
    assert "kein live-trading" in doc


# 10: Doku benennt ausdrücklich nur lokale Fixtures und tmp_path.
def test_doc_states_local_fixtures_and_tmp_path():
    doc = _doc().lower()
    assert "tmp_path" in doc
    assert "lokale fixtures" in doc


# 11: Doku benennt ausdrücklich, dass keine Produktionslogik geändert wurde.
def test_doc_states_no_production_logic_change():
    assert "keine Produktionslogik geändert" in _doc()


# 12: keine NEU committeten CSV-/Screenshot-/Report-Artefakte im docs-Verzeichnis
#     (Fixture-Namen im Doku-TEXT sind erlaubt; geprüft wird das Dateisystem).
def test_no_real_artefacts_in_docs():
    docs = _ROOT / "docs"
    for pattern in ("*.csv", "*.png", "*.jpg", "*.jpeg", "*.pdf"):
        assert not list(docs.glob(pattern)), f"unerwartetes Artefakt: {pattern}"
