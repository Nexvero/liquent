"""Doku-Tests für die Controlled Local Streamlit Smoke-Test Checklist (LQ-028).

Prüft die Checklist-Doku + README/Index/Roadmap-Verlinkung, ohne fragil zu
sein. Kein Streamlit, kein Netzwerk, keine echten Daten, keine Installation.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "lq-028-controlled-streamlit-smoke-test-checklist.md"
_README = _ROOT / "README.md"
_INDEX = _ROOT / "docs" / "visual-preview-index.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"

_DOC_NAME = "lq-028-controlled-streamlit-smoke-test-checklist.md"


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


# 1: LQ-028-Doku existiert.
def test_smoke_checklist_doc_exists():
    assert _DOC.is_file()


# 2-9: Doku enthält die Kernabschnitte.
def test_doc_has_core_sections():
    doc = _doc()
    for heading in (
        "Preconditions",
        "Streamlit Availability Check",
        "Local App Start",
        "Manual UI Smoke-Test Checklist",
        "Synthetic Dataset Smoke Tests",
        "CSV Smoke Tests Without Persisted Files",
        "Post-Test Cleanup",
        "Pass/Fail-Kriterien",
    ):
        assert heading in doc, f"Checklist-Doku fehlt Abschnitt: {heading!r}"


# Doku enthält die zentralen Smoke-/Verfügbarkeits-Befehle.
def test_doc_has_core_commands():
    doc = _doc()
    assert "python -m pytest" in doc
    assert "python -m tools.visual_preview.app" in doc
    assert "streamlit run tools/visual_preview/app.py" in doc
    assert "importlib.util.find_spec" in doc


# Doku bleibt Doku-only: kein automatischer Installations-/Start-Zwang, sondern
# explizit als manuelle Option markiert.
def test_doc_marks_installation_as_manual_option():
    doc = _doc()
    assert 'pip install -e ".[visual]"' in doc
    assert "Optional Manual Installation" in doc


# 10: README verlinkt LQ-028.
def test_readme_links_checklist():
    assert _DOC_NAME in _README.read_text(encoding="utf-8")


# 11: Index verlinkt LQ-028.
def test_index_links_checklist():
    assert _DOC_NAME in _INDEX.read_text(encoding="utf-8")


# Roadmap verlinkt LQ-028.
def test_roadmap_links_checklist():
    assert _DOC_NAME in _ROADMAP.read_text(encoding="utf-8")


def _roadmap_visual_preview_section() -> str:
    """Nur der von LQ-028 berührte Visual-Preview-Abschnitt der Roadmap.

    Die Roadmap enthält an anderer Stelle eine bestehende Meta-Disclaimer-Zeile
    (`kein Ranking/winner/better/worse`); diese soll der Wertungs-Scan nicht
    fälschlich treffen.
    """
    text = _ROADMAP.read_text(encoding="utf-8")
    marker = "## 11. Visual Preview"
    return text[text.index(marker):] if marker in text else ""


# 12: keine verbotene Wertungssprache (fragment-gebaute Liste, damit diese
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


# 13: keine echte CSV-Datei im docs-Verzeichnis.
def test_no_real_csv_files_in_docs():
    assert not list((_ROOT / "docs").glob("*.csv"))
