"""Doku-Tests für den No-Execution-Checkpoint (LQ-032).

Prüft die No-Execution-Checkpoint-Doku + README/Index/Roadmap-Verlinkung, ohne
fragil zu sein. Kein Streamlit, kein Netzwerk, keine echten Daten, keine
Installation.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "lq-032-streamlit-install-decision-no-execution-checkpoint.md"
_README = _ROOT / "README.md"
_INDEX = _ROOT / "docs" / "visual-preview-index.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"

_DOC_NAME = "lq-032-streamlit-install-decision-no-execution-checkpoint.md"


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


# 1: LQ-032-Doku existiert.
def test_no_execution_doc_exists():
    assert _DOC.is_file()


# 2-10: Doku enthält die Kernabschnitte.
def test_doc_has_core_sections():
    doc = _doc()
    for heading in (
        "Current No-Execution State",
        "Option A",
        "Option B",
        "Option C",
        "Option D",
        "Recommended Decision",
        "Required Checks for No-Execution Checkpoint",
        "If Installation Is Later Approved",
        "If UI Execution Is Later Approved",
    ):
        assert heading in doc, f"No-Execution-Doku fehlt Abschnitt: {heading!r}"


# Doku bleibt Doku-only: kein automatischer Streamlit-Start, Installation nur
# als spätere Option markiert.
def test_doc_keeps_no_execution_state():
    doc = _doc()
    assert 'pip install -e ".[visual]"' in doc
    assert "No Streamlit start." in doc
    assert "keep no-execution state" in doc.lower()


# 11: README verlinkt LQ-032.
def test_readme_links_no_execution_checkpoint():
    assert _DOC_NAME in _README.read_text(encoding="utf-8")


# 12: Index verlinkt LQ-032.
def test_index_links_no_execution_checkpoint():
    assert _DOC_NAME in _INDEX.read_text(encoding="utf-8")


# 13: Roadmap verlinkt LQ-032.
def test_roadmap_links_no_execution_checkpoint():
    assert _DOC_NAME in _ROADMAP.read_text(encoding="utf-8")


def _roadmap_visual_preview_section() -> str:
    """Nur der von LQ-032 berührte Visual-Preview-Abschnitt der Roadmap.

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
