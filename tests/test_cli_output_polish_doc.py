"""Doku-/Link-Tests für die CLI-Output-Polish-Doku (LQ-044 Phase 2).

Prüft die finalisierte Doku + README/Roadmap-Verlinkung, ohne fragil zu sein.
Kein Streamlit, kein Netzwerk, keine echten Daten, keine Codeänderung. Importiert
keine Produktionslogik und erzeugt keine Artefakte.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "lq-044-cli-output-polish.md"
_README = _ROOT / "README.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"
_VP_INDEX = _ROOT / "docs" / "visual-preview-index.md"

_DOC_NAME = "lq-044-cli-output-polish.md"


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


# 1: LQ-044-Doku existiert.
def test_spec_doc_exists():
    assert _DOC.is_file()


# 2: Doku enthält die zentralen Abschnitte.
def test_doc_has_core_sections():
    doc = _doc()
    for heading in (
        "Status",
        "Purpose",
        "Verified Current Model",
        "CLI Contract",
        "Exit-Code Contract",
        "Validation Contract",
        "Bool Parsing Contract",
        "Output/Framing Contract",
        "Help Contract",
        "Error-Message Contract",
        "Terminal Output Contract",
        "File Output Contract",
        "Descriptive-only / Safety Invariants",
        "Edge-Case Table",
        "Regression Invariants",
        "Safety Boundaries",
        "Test Plan",
        "Non-Goals",
        "Deferred Topics",
        "Implementation Status",
    ):
        assert heading in doc, f"LQ-044-Doku fehlt Abschnitt: {heading!r}"


# 3: Doku verankert verifizierte echte Identifier (kein erfundenes Feld).
def test_doc_documents_real_identifiers():
    doc = _doc()
    for token in (
        "backtest_mid_breakout",
        "_EXIT_OK",
        "_EXIT_RUNTIME",
        "_EXIT_USAGE",
        "_validate_ranges",
        "_resolve_strategy_args",
        "_parse_bool",
        "--overwrite",
    ):
        assert token in doc, f"LQ-044-Doku fehlt verifizierter Bezeichner: {token!r}"


# 4: README verlinkt LQ-044.
def test_readme_links_doc():
    assert _DOC_NAME in _README.read_text(encoding="utf-8")


# 5: Roadmap verlinkt LQ-044.
def test_roadmap_links_doc():
    assert _DOC_NAME in _ROADMAP.read_text(encoding="utf-8")


# 6: Visual Preview Index enthält NICHT LQ-044.
def test_visual_preview_index_has_no_lq044():
    text = _VP_INDEX.read_text(encoding="utf-8").lower()
    assert _DOC_NAME not in text
    assert "lq-044" not in text


# 7: keine verbotene Wertungssprache in der LQ-044-Doku (fragment-gebaute Liste,
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


# 8: keine Artefakt-Referenzen in der LQ-044-Doku.
def test_doc_has_no_artefact_references():
    doc = _doc().lower()
    for ext in (".csv", ".png", ".jpg", ".jpeg", ".pdf"):
        assert ext not in doc, f"LQ-044-Doku referenziert Artefakt-Typ: {ext!r}"


# 9: Doku benennt ausdrücklich, dass es keine neuen Flags/Exit-Codes/Output-Formate gibt.
def test_doc_states_no_new_flags_exit_codes_formats():
    # Whitespace normalisieren, damit Zeilenumbrüche die Prüfung nicht stören.
    doc = " ".join(_doc().lower().split())
    for token in ("keine neuen cli-flags", "keine neuen exit-codes", "keine neuen output-formate"):
        assert token in doc, f"LQ-044-Doku benennt nicht ausdrücklich: {token!r}"


# 10: Doku benennt ausdrücklich keine Live-/Paper-/Exchange-Anbindung.
def test_doc_states_no_live_paper_exchange():
    doc = _doc().lower()
    assert "kein paper-trading" in doc
    assert "kein live-trading" in doc
    assert "api-/exchange-anbindung" in doc


# 11: Doku benennt ausdrücklich Test-Outputs nur über tmp_path.
def test_doc_states_outputs_only_via_tmp_path():
    assert "tmp_path" in _doc()


# 12: keine echten CSV-/Screenshot-/Report-Artefakte im docs-Verzeichnis.
def test_no_real_artefacts_in_docs():
    docs = _ROOT / "docs"
    for pattern in ("*.csv", "*.png", "*.jpg", "*.jpeg", "*.pdf"):
        assert not list(docs.glob(pattern)), f"unerwartetes Artefakt: {pattern}"
