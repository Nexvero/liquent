"""Doku-Tests für den Visual-Preview-Stabilization-Checkpoint (LQ-027 Phase 2).

Prüft die Checkpoint-Doku + README/Index/Roadmap-Verlinkung, ohne fragil zu
sein. Kein Streamlit, kein Netzwerk, keine echten Daten.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "lq-027-visual-preview-stabilization-checkpoint.md"
_README = _ROOT / "README.md"
_INDEX = _ROOT / "docs" / "visual-preview-index.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"

_DOC_NAME = "lq-027-visual-preview-stabilization-checkpoint.md"


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


# 1: Checkpoint-Doku existiert.
def test_checkpoint_doc_exists():
    assert _DOC.is_file()


# 2-6: Doku enthält die Kernabschnitte.
def test_doc_has_core_sections():
    doc = _doc()
    for heading in (
        "Smoke Checks",
        "Release Criteria",
        "Known Boundaries",
        "Safety Boundaries",
        "Recommended Next Development Paths",
    ):
        assert heading in doc, f"Checkpoint-Doku fehlt Abschnitt: {heading!r}"


# 7: Doku enthält die Smoke-Check-Befehle.
def test_doc_has_smoke_commands():
    doc = _doc()
    assert "python -m pytest" in doc
    assert "python -m tools.visual_preview.app" in doc
    assert "streamlit run tools/visual_preview/app.py" in doc


# 8: README verlinkt die Checkpoint-Doku.
def test_readme_links_checkpoint():
    assert _DOC_NAME in _README.read_text(encoding="utf-8")


# 9: Index verlinkt LQ-027.
def test_index_links_checkpoint():
    assert _DOC_NAME in _INDEX.read_text(encoding="utf-8")


# 10: Roadmap verlinkt LQ-027.
def test_roadmap_links_checkpoint():
    assert _DOC_NAME in _ROADMAP.read_text(encoding="utf-8")


def _roadmap_visual_preview_section() -> str:
    """Nur der von LQ-027 berührte Visual-Preview-Abschnitt der Roadmap.

    Die Roadmap enthält an anderer Stelle eine bestehende Meta-Disclaimer-Zeile
    (`kein Ranking/winner/better/worse`); diese soll der Wertungs-Scan nicht
    fälschlich treffen.
    """
    text = _ROADMAP.read_text(encoding="utf-8")
    marker = "## 11. Visual Preview"
    return text[text.index(marker):] if marker in text else ""


# 11: keine verbotene Wertungssprache (fragment-gebaute Liste, damit diese
# Testdatei sich nicht selbst matcht). "recommendation" bleibt erlaubt. Der
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


# 12: keine echte CSV-Datei im docs-Verzeichnis.
def test_no_real_csv_files_in_docs():
    assert not list((_ROOT / "docs").glob("*.csv"))
