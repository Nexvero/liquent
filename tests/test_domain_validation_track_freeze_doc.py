"""Doku-/Link-Tests für die Domain-Validation-Track-Freeze-Entscheidung (LQ-050 Phase 2).

Prüft die finalisierte Freeze-/Next-Track-Decision-Doku + README/Roadmap-
Verlinkung, ohne fragil zu sein. Kein Streamlit, kein Netzwerk, keine echten
Daten, keine Codeänderung. Importiert keine Produktionslogik und erzeugt keine
Artefakte.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "lq-050-domain-model-validation-track-freeze.md"
_README = _ROOT / "README.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"
_VP_INDEX = _ROOT / "docs" / "visual-preview-index.md"

_DOC_NAME = "lq-050-domain-model-validation-track-freeze.md"


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


# 1: LQ-050-Doku existiert.
def test_spec_doc_exists():
    assert _DOC.is_file()


# 2-11: zentrale Abschnitte + Optionen A-D.
def test_doc_has_core_sections():
    doc = _doc()
    for heading in (
        "Current Domain Validation Contract",
        "Decision Options",
        "Option A",
        "Option B",
        "Option C",
        "Option D",
        "Recommended Decision",
        "Possible Next Tracks",
        "Conditions Before Any Validator Implementation",
        "Safety Boundaries",
    ):
        assert heading in doc, f"LQ-050-Doku fehlt Abschnitt: {heading!r}"


# 12: Roadmap verlinkt LQ-050.
def test_roadmap_links_doc():
    assert _DOC_NAME in _ROADMAP.read_text(encoding="utf-8")


# 13: README verlinkt LQ-050.
def test_readme_links_doc():
    assert _DOC_NAME in _README.read_text(encoding="utf-8")


# 14: Visual Preview Index enthält NICHT LQ-050.
def test_visual_preview_index_has_no_lq050():
    text = _VP_INDEX.read_text(encoding="utf-8").lower()
    assert _DOC_NAME not in text
    assert "lq-050" not in text


# 15: keine verbotene Wertungssprache — die zu prüfenden Begriffe werden per
# String-Fragmenten zusammengebaut, damit weder Doku noch diese Testdatei sich
# selbst matchen.
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


# 16: keine echten CSV-/Screenshot-/Report-Artefakte im docs-Verzeichnis.
def test_no_real_artefacts_in_docs():
    docs = _ROOT / "docs"
    for pattern in ("*.csv", "*.png", "*.jpg", "*.jpeg", "*.pdf"):
        assert not list(docs.glob(pattern)), f"unerwartetes Artefakt: {pattern}"
