"""Doku-Tests für den Visual-Preview-Docs-Index (LQ-026 Phase 2).

Prüft den zentralen Index + README/Roadmap-Navigationslinks, ohne fragil zu
sein. Kein Streamlit, kein Netzwerk, keine echten Daten.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_INDEX = _ROOT / "docs" / "visual-preview-index.md"
_README = _ROOT / "README.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"

_LQ_DOCS = (
    "lq-019-visual-dashboard-local-preview.md",
    "lq-020-visual-preview-streamlit-setup.md",
    "lq-021-visual-preview-ui-polish-signal-chart.md",
    "lq-022-visual-preview-local-csv-upload.md",
    "lq-023-visual-preview-csv-validation-ux.md",
    "lq-024-visual-preview-csv-schema-variants.md",
    "lq-025-visual-preview-quickstart.md",
)


def _index() -> str:
    return _INDEX.read_text(encoding="utf-8")


def _readme() -> str:
    return _README.read_text(encoding="utf-8")


# 1: Index existiert.
def test_index_exists():
    assert _INDEX.is_file()


# 2: Index verlinkt alle LQ-019..LQ-025-Dokumente.
def test_index_links_all_lq_docs():
    index = _index()
    for name in _LQ_DOCS:
        assert name in index, f"Index fehlt Link auf {name}"


# 3: Index enthält Current capabilities.
def test_index_has_current_capabilities():
    assert "Current capabilities" in _index()


# 4: Index enthält Safety boundaries.
def test_index_has_safety_boundaries():
    assert "Safety boundaries" in _index()


# 5/6: Index enthält die Safety-Hinweise.
def test_index_has_safety_notes():
    index = _index()
    assert "No live trading" in index
    assert "No trading recommendation" in index


# 7: README verlinkt den Index.
def test_readme_links_index():
    assert "docs/visual-preview-index.md" in _readme()


# 8: README verlinkt den Quickstart.
def test_readme_links_quickstart():
    assert "docs/lq-025-visual-preview-quickstart.md" in _readme()


# 9: Roadmap verlinkt den Index (da ergänzt).
def test_roadmap_links_index():
    assert "docs/visual-preview-index.md" in _ROADMAP.read_text(encoding="utf-8")


# 10: keine verbotene Wertungssprache (fragment-gebaute Liste, damit diese
# Testdatei sich nicht selbst matcht). "recommendation" bleibt erlaubt.
def test_no_forbidden_valuation_language():
    combined = (_index() + _readme()).lower()
    forbidden = [
        "profit" + "able",
        "win" + "ner",
        "guar" + "anteed",
        "best " + "strategy",
        "should " + "trade",
    ]
    for token in forbidden:
        assert token not in combined, f"verbotener Wertungsbegriff: {token!r}"


# 11: keine echte CSV-Datei im Repo-docs-Verzeichnis.
def test_no_real_csv_files_in_docs():
    assert not list((_ROOT / "docs").glob("*.csv"))
