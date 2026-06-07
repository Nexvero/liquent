"""Doku-/Link-Tests für den Architecture Review Checkpoint (LQ-052 Phase 2).

Prüft die finalisierte Architecture-Review-Doku + README/Roadmap-Verlinkung,
ohne fragil zu sein. Kein Streamlit, kein Netzwerk, keine echten Daten, keine
Codeänderung. Importiert keine Produktionslogik und erzeugt keine Artefakte.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "lq-052-architecture-review-checkpoint.md"
_README = _ROOT / "README.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"
_VP_INDEX = _ROOT / "docs" / "visual-preview-index.md"

_DOC_NAME = "lq-052-architecture-review-checkpoint.md"


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


# 1: LQ-052-Doku existiert.
def test_spec_doc_exists():
    assert _DOC.is_file()


# 2-8: zentrale Abschnitte.
def test_doc_has_core_sections():
    doc = _doc()
    for heading in (
        "Architecture Inventory",
        "Frozen Tracks",
        "Parked Future Specs",
        "Architecture Risks",
        "Recommended Architecture Decision",
        "Possible LQ-053 Directions",
        "Safety Boundaries",
    ):
        assert heading in doc, f"LQ-052-Doku fehlt Abschnitt: {heading!r}"


# 9: Roadmap verlinkt LQ-052.
def test_roadmap_links_doc():
    assert _DOC_NAME in _ROADMAP.read_text(encoding="utf-8")


# 10: README verlinkt LQ-052.
def test_readme_links_doc():
    assert _DOC_NAME in _README.read_text(encoding="utf-8")


# 11: Visual Preview Index enthält NICHT LQ-052.
def test_visual_preview_index_has_no_lq052():
    text = _VP_INDEX.read_text(encoding="utf-8").lower()
    assert _DOC_NAME not in text
    assert "lq-052" not in text


# 12: keine verbotene Wertungssprache — die zu prüfenden Begriffe werden per
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


# 13: keine echten CSV-/Screenshot-/Report-Artefakte im docs-Verzeichnis.
def test_no_real_artefacts_in_docs():
    docs = _ROOT / "docs"
    for pattern in ("*.csv", "*.png", "*.jpg", "*.jpeg", "*.pdf"):
        assert not list(docs.glob(pattern)), f"unerwartetes Artefakt: {pattern}"
