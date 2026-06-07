"""Doku-/Link-Tests für die Domain-Model-Invariants-/Validation-Decision (LQ-048 Phase 2).

Prüft die finalisierte Decision-Doku + README/Roadmap-Verlinkung, ohne fragil zu
sein. Kein Streamlit, kein Netzwerk, keine echten Daten, keine Codeänderung.
Importiert keine Produktionslogik und erzeugt keine Artefakte.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "lq-048-domain-model-invariants-validation-decision.md"
_README = _ROOT / "README.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"
_VP_INDEX = _ROOT / "docs" / "visual-preview-index.md"

_DOC_NAME = "lq-048-domain-model-invariants-validation-decision.md"


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


# 1: LQ-048-Doku existiert.
def test_spec_doc_exists():
    assert _DOC.is_file()


# 2-13: zentrale Abschnitte + Optionen A-E.
def test_doc_has_core_sections():
    doc = _doc()
    for heading in (
        "Verified Current Domain Model",
        "Candidate Invariants",
        "Validation Placement Options",
        "Option A",
        "Option B",
        "Option C",
        "Option D",
        "Option E",
        "Recommended Decision",
        "Recommended Future Test Strategy",
        "Compatibility / Risk Analysis",
        "Safety Boundaries",
    ):
        assert heading in doc, f"LQ-048-Doku fehlt Abschnitt: {heading!r}"


# 14: Roadmap verlinkt LQ-048.
def test_roadmap_links_doc():
    assert _DOC_NAME in _ROADMAP.read_text(encoding="utf-8")


# 15: README verlinkt LQ-048.
def test_readme_links_doc():
    assert _DOC_NAME in _README.read_text(encoding="utf-8")


# 16: Visual Preview Index enthält NICHT LQ-048.
def test_visual_preview_index_has_no_lq048():
    text = _VP_INDEX.read_text(encoding="utf-8").lower()
    assert _DOC_NAME not in text
    assert "lq-048" not in text


# 17: Doku enthält echte Feldnamen.
def test_doc_documents_real_field_names():
    doc = _doc()
    for token in ("spread", "depth", "imbalance", "entry", "size", "metriken"):
        assert token in doc, f"LQ-048-Doku fehlt echter Feldname: {token!r}"


# 18: Doku behauptet KEINE erfundenen Felder als echte Struktur. Die Begriffe
# dürfen nur in expliziten Negativ-/Disclaimer-Sätzen vorkommen — geprüft über
# die exakten Disclaimer-Phrasen.
def test_doc_disclaims_non_existing_fields():
    doc = _doc()
    for phrase in (
        "value/score/rating-Felder",
        "kein quantity-Feld behaupten",
        "kein entry_price-Feld behaupten",
        "kein metrics-Feld behaupten",
    ):
        assert phrase in doc, f"LQ-048-Doku fehlt Disclaimer-Phrase: {phrase!r}"


# 19: keine verbotene Wertungssprache (fragment-gebaute Liste, damit weder Doku
# noch diese Testdatei sich selbst matchen).
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


# 20: keine echten CSV-/Screenshot-/Report-Artefakte im docs-Verzeichnis.
def test_no_real_artefacts_in_docs():
    docs = _ROOT / "docs"
    for pattern in ("*.csv", "*.png", "*.jpg", "*.jpeg", "*.pdf"):
        assert not list(docs.glob(pattern)), f"unerwartetes Artefakt: {pattern}"
