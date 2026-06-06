"""Doku-Tests für den Manual Streamlit Smoke-Test Execution Plan (LQ-030).

Prüft die Execution-Plan-Doku + README/Index/Roadmap-Verlinkung, ohne fragil zu
sein. Kein Streamlit, kein Netzwerk, keine echten Daten, keine Installation.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "lq-030-manual-streamlit-smoke-test-execution-plan.md"
_README = _ROOT / "README.md"
_INDEX = _ROOT / "docs" / "visual-preview-index.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"

_DOC_NAME = "lq-030-manual-streamlit-smoke-test-execution-plan.md"


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


# 1: LQ-030-Doku existiert.
def test_execution_plan_doc_exists():
    assert _DOC.is_file()


# 2-11: Doku enthält die Kernabschnitte.
def test_doc_has_core_sections():
    doc = _doc()
    for heading in (
        "Preconditions",
        "Streamlit Availability Decision",
        "Optional Manual Installation Gate",
        "Manual App Start Plan",
        "UI Smoke-Test Matrix",
        "Synthetic Dataset Test Cases",
        "CSV Test Cases Without Persisted Files",
        "Post-Test Cleanup",
        "Result Logging Template",
        "Pass/Fail Criteria",
    ):
        assert heading in doc, f"Execution-Plan-Doku fehlt Abschnitt: {heading!r}"


# Doku bleibt Doku-only: Installation explizit als manuelles Gate markiert,
# kein automatischer Streamlit-Start.
def test_doc_marks_installation_as_manual_gate():
    doc = _doc()
    assert 'pip install -e ".[visual]"' in doc
    assert "No Streamlit start." in doc


# 12: README verlinkt LQ-030.
def test_readme_links_execution_plan():
    assert _DOC_NAME in _README.read_text(encoding="utf-8")


# 13: Index verlinkt LQ-030.
def test_index_links_execution_plan():
    assert _DOC_NAME in _INDEX.read_text(encoding="utf-8")


# 14: Roadmap verlinkt LQ-030.
def test_roadmap_links_execution_plan():
    assert _DOC_NAME in _ROADMAP.read_text(encoding="utf-8")


def _roadmap_visual_preview_section() -> str:
    """Nur der von LQ-030 berührte Visual-Preview-Abschnitt der Roadmap.

    Die Roadmap enthält an anderer Stelle eine bestehende Meta-Disclaimer-Zeile
    (`kein Ranking/winner/better/worse`); diese soll der Wertungs-Scan nicht
    fälschlich treffen.
    """
    text = _ROADMAP.read_text(encoding="utf-8")
    marker = "## 11. Visual Preview"
    return text[text.index(marker):] if marker in text else ""


# 15: keine verbotene Wertungssprache (fragment-gebaute Liste, damit diese
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


# 16: keine echte CSV-Datei im docs-Verzeichnis.
def test_no_real_csv_files_in_docs():
    assert not list((_ROOT / "docs").glob("*.csv"))
