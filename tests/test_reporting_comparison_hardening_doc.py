"""Doku-/Link-Tests für die Reporting-/Comparison-Stabilization-Doku (LQ-043 Phase 2).

Prüft die finalisierte Doku + README/Roadmap-Verlinkung, ohne fragil zu sein.
Kein Streamlit, kein Netzwerk, keine echten Daten, keine Codeänderung. Importiert
keine Produktionslogik und erzeugt keine Artefakte.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "lq-043-reporting-comparison-stabilization.md"
_README = _ROOT / "README.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"
_VP_INDEX = _ROOT / "docs" / "visual-preview-index.md"

_DOC_NAME = "lq-043-reporting-comparison-stabilization.md"


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


# 1: LQ-043-Doku existiert.
def test_spec_doc_exists():
    assert _DOC.is_file()


# 2: Doku enthält die zentralen Abschnitte.
def test_doc_has_core_sections():
    doc = _doc()
    for heading in (
        "Status",
        "Purpose",
        "Verified Current Model",
        "Reporting Contract",
        "BacktestExperimentSummary Contract",
        "summarize_backtest_result Contract",
        "summary_to_markdown Contract",
        "summary_to_dict Contract",
        "Comparison Reporting Contract",
        "Normalization Contract",
        "Output Contract",
        "Descriptive-only Invariants",
        "Edge-Case Table",
        "Regression Invariants",
        "Safety Boundaries",
        "Test Plan",
        "Non-Goals",
        "Deferred Topics",
        "Implementation Status",
    ):
        assert heading in doc, f"LQ-043-Doku fehlt Abschnitt: {heading!r}"


# 3: Doku verankert verifizierte echte Identifier (kein erfundenes Feld).
def test_doc_documents_real_identifiers():
    doc = _doc()
    for token in (
        "BacktestExperimentSummary",
        "summarize_backtest_result",
        "summary_to_markdown",
        "summary_to_dict",
        "normalize_comparison",
        "render_comparison_markdown",
        "strategy_metadata",
        "cost_metadata",
    ):
        assert token in doc, f"LQ-043-Doku fehlt verifizierter Bezeichner: {token!r}"


# 4: README verlinkt LQ-043.
def test_readme_links_doc():
    assert _DOC_NAME in _README.read_text(encoding="utf-8")


# 5: Roadmap verlinkt LQ-043.
def test_roadmap_links_doc():
    assert _DOC_NAME in _ROADMAP.read_text(encoding="utf-8")


# 6: Visual Preview Index enthält NICHT LQ-043.
def test_visual_preview_index_has_no_lq043():
    text = _VP_INDEX.read_text(encoding="utf-8").lower()
    assert _DOC_NAME not in text
    assert "lq-043" not in text


# 7: keine verbotene Wertungssprache in der LQ-043-Doku (fragment-gebaute Liste,
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


# 8: keine Artefakt-Referenzen in der LQ-043-Doku.
def test_doc_has_no_artefact_references():
    doc = _doc().lower()
    for ext in (".csv", ".png", ".jpg", ".jpeg", ".pdf"):
        assert ext not in doc, f"LQ-043-Doku referenziert Artefakt-Typ: {ext!r}"


# 9: Doku benennt ausdrücklich, dass es keine Ranking-/Bewertungs-/Empfehlungslogik gibt.
def test_doc_states_no_ranking_evaluation_recommendation():
    doc = _doc().lower()
    for token in ("ranking", "bewertung", "empfehlung"):
        assert token in doc, f"LQ-043-Doku benennt nicht ausdrücklich: {token!r}"


# 10: Doku benennt Reihenfolge ausdrücklich als technischen Output-Contract.
def test_doc_states_order_is_technical_output_contract():
    doc = _doc().lower()
    assert "output-contract" in doc or "output contract" in doc


# 11: keine echten CSV-/Screenshot-/Report-Artefakte im docs-Verzeichnis.
def test_no_real_artefacts_in_docs():
    docs = _ROOT / "docs"
    for pattern in ("*.csv", "*.png", "*.jpg", "*.jpeg", "*.pdf"):
        assert not list(docs.glob(pattern)), f"unerwartetes Artefakt: {pattern}"
