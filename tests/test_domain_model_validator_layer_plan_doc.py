"""Doku-/Link-Tests für den Domain-Model-Validator-Layer-Plan (LQ-049 Phase 2).

Prüft die finalisierte Plan-Doku + README/Roadmap-Verlinkung, ohne fragil zu
sein. Kein Streamlit, kein Netzwerk, keine echten Daten, keine Codeänderung.
Importiert keine Produktionslogik und erzeugt keine Artefakte.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "lq-049-domain-model-validator-layer-plan.md"
_README = _ROOT / "README.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"
_VP_INDEX = _ROOT / "docs" / "visual-preview-index.md"

_DOC_NAME = "lq-049-domain-model-validator-layer-plan.md"


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


# 1: LQ-049-Doku existiert.
def test_spec_doc_exists():
    assert _DOC.is_file()


# 2-13: zentrale Abschnitte + Optionen A-E.
def test_doc_has_core_sections():
    doc = _doc()
    for heading in (
        "Validator Layer Scope Options",
        "Option A",
        "Option B",
        "Option C",
        "Option D",
        "Option E",
        "Recommended Decision",
        "Candidate Validator API",
        "Candidate Validation Rules",
        "Placement / Responsibility Boundaries",
        "Future Implementation Plan",
        "Safety Boundaries",
    ):
        assert heading in doc, f"LQ-049-Doku fehlt Abschnitt: {heading!r}"


# 14: Roadmap verlinkt LQ-049.
def test_roadmap_links_doc():
    assert _DOC_NAME in _ROADMAP.read_text(encoding="utf-8")


# 15: README verlinkt LQ-049.
def test_readme_links_doc():
    assert _DOC_NAME in _README.read_text(encoding="utf-8")


# 16: Visual Preview Index enthält NICHT LQ-049.
def test_visual_preview_index_has_no_lq049():
    text = _VP_INDEX.read_text(encoding="utf-8").lower()
    assert _DOC_NAME not in text
    assert "lq-049" not in text


# 17: Doku enthält echte Feldnamen.
def test_doc_documents_real_field_names():
    doc = _doc()
    for token in ("spread", "depth", "imbalance", "entry", "size", "metriken"):
        assert token in doc, f"LQ-049-Doku fehlt echter Feldname: {token!r}"


# 18+19: Doku markiert die Validator-Funktionen ausdrücklich als (noch) nicht
# existent — sie dürfen nur als Zukunftsentwurf vorkommen, nicht als vorhandene
# Implementierung.
def test_doc_marks_validators_as_not_existing():
    doc = _doc()
    assert "Diese Funktionen existieren aktuell nicht." in doc
    assert "In LQ-049 werden sie nicht implementiert." in doc


# 20: keine verbotene Wertungssprache (fragment-gebaute Liste).
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


# 21: keine echten CSV-/Screenshot-/Report-Artefakte im docs-Verzeichnis.
def test_no_real_artefacts_in_docs():
    docs = _ROOT / "docs"
    for pattern in ("*.csv", "*.png", "*.jpg", "*.jpeg", "*.pdf"):
        assert not list(docs.glob(pattern)), f"unerwartetes Artefakt: {pattern}"
