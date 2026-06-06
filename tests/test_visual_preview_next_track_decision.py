"""Doku-Tests für die Review-Pause / Next-Track-Entscheidungsvorlage (LQ-029).

Prüft die Entscheidungs-Doku + README/Index/Roadmap-Verlinkung, ohne fragil zu
sein. Kein Streamlit, kein Netzwerk, keine echten Daten, keine Installation.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "lq-029-visual-preview-review-pause-next-track.md"
_README = _ROOT / "README.md"
_INDEX = _ROOT / "docs" / "visual-preview-index.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"

_DOC_NAME = "lq-029-visual-preview-review-pause-next-track.md"


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


# 1: LQ-029-Doku existiert.
def test_next_track_doc_exists():
    assert _DOC.is_file()


# 2: Doku enthält Current Checkpoint Summary.
def test_doc_has_checkpoint_summary():
    assert "Current Checkpoint Summary" in _doc()


# 3-7: Doku enthält alle Tracks A-E.
def test_doc_has_all_tracks():
    doc = _doc()
    for track in ("Track A", "Track B", "Track C", "Track D", "Track E"):
        assert track in doc, f"Doku fehlt {track!r}"


# 8: Doku enthält Decision Criteria.
def test_doc_has_decision_criteria():
    assert "Decision Criteria" in _doc()


# 9: Doku enthält Empfehlung für LQ-030 oder Pause/Review.
def test_doc_has_recommended_decision():
    doc = _doc()
    assert "LQ-030 Phase 1" in doc or "Pause/Review" in doc


# 10: Doku enthält Safety Boundaries.
def test_doc_has_safety_boundaries():
    assert "Safety Boundaries" in _doc()


# 11: Index verlinkt LQ-029.
def test_index_links_next_track():
    assert _DOC_NAME in _INDEX.read_text(encoding="utf-8")


# 12: README verlinkt LQ-029.
def test_readme_links_next_track():
    assert _DOC_NAME in _README.read_text(encoding="utf-8")


# 13: Roadmap verlinkt LQ-029.
def test_roadmap_links_next_track():
    assert _DOC_NAME in _ROADMAP.read_text(encoding="utf-8")


def _roadmap_visual_preview_section() -> str:
    """Nur der von LQ-029 berührte Visual-Preview-Abschnitt der Roadmap.

    Die Roadmap enthält an anderer Stelle eine bestehende Meta-Disclaimer-Zeile
    (`kein Ranking/winner/better/worse`); diese soll der Wertungs-Scan nicht
    fälschlich treffen.
    """
    text = _ROADMAP.read_text(encoding="utf-8")
    marker = "## 11. Visual Preview"
    return text[text.index(marker):] if marker in text else ""


# 14: keine verbotene Wertungssprache (fragment-gebaute Liste, damit diese
# Testdatei sich nicht selbst matcht). "recommendation" bleibt erlaubt; der
# Roadmap-Anteil ist auf den Visual-Preview-Abschnitt beschränkt (s. o.).
def test_no_forbidden_valuation_language():
    combined = (
        _doc()
        + _README.read_text(encoding="utf-8")
        + _INDEX.read_text(encoding="utf-8")
        + _roadmap_visual_preview_section()
    ).lower()
    forbidden = [
        "profit" + "able",
        "win" + "ner",
        "guar" + "anteed",
        "best " + "strategy",
        "should " + "trade",
    ]
    for token in forbidden:
        assert token not in combined, f"verbotener Wertungsbegriff: {token!r}"


# 15: keine echte CSV-Datei im docs-Verzeichnis.
def test_no_real_csv_files_in_docs():
    assert not list((_ROOT / "docs").glob("*.csv"))
