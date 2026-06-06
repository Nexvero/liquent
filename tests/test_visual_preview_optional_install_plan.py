"""Doku-Tests für den Optional Streamlit Install Execution Plan (LQ-033).

Prüft die Install-Plan-Doku + README/Index/Roadmap-Verlinkung, ohne fragil zu
sein. Kein Streamlit, kein Netzwerk, keine echten Daten, keine Installation.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "lq-033-optional-streamlit-install-execution-plan.md"
_README = _ROOT / "README.md"
_INDEX = _ROOT / "docs" / "visual-preview-index.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"

_DOC_NAME = "lq-033-optional-streamlit-install-execution-plan.md"


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


# 1: LQ-033-Doku existiert.
def test_optional_install_doc_exists():
    assert _DOC.is_file()


# 2-11: Doku enthält die Kernabschnitte.
def test_doc_has_core_sections():
    doc = _doc()
    for heading in (
        "Installation Gate",
        "Gate A",
        "Gate B",
        "Gate C",
        "Gate D",
        "Pre-Install Checks",
        "Install Command Options",
        "Post-Install Checks",
        "UI Start Is Separate",
        "Rollback / Cleanup Considerations",
    ):
        assert heading in doc, f"Install-Plan-Doku fehlt Abschnitt: {heading!r}"


# Doku bleibt Doku-only: kein automatischer Streamlit-Start, Installation nur
# als gegated/separat freigegeben markiert.
def test_doc_keeps_install_gated():
    doc = _doc()
    assert 'pip install -e ".[visual]"' in doc
    assert "No Streamlit start." in doc
    assert "No dependency installed." in doc


# 12: README verlinkt LQ-033.
def test_readme_links_optional_install_plan():
    assert _DOC_NAME in _README.read_text(encoding="utf-8")


# 13: Index verlinkt LQ-033.
def test_index_links_optional_install_plan():
    assert _DOC_NAME in _INDEX.read_text(encoding="utf-8")


# 14: Roadmap verlinkt LQ-033.
def test_roadmap_links_optional_install_plan():
    assert _DOC_NAME in _ROADMAP.read_text(encoding="utf-8")


def _roadmap_visual_preview_section() -> str:
    """Nur der von LQ-033 berührte Visual-Preview-Abschnitt der Roadmap.

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
