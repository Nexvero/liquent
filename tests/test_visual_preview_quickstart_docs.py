"""Doku-Tests für den Visual-Preview-Quickstart (LQ-025 Phase 2).

Prüft README-Quickstart + ausführliche docs-Datei auf die erwarteten Inhalte,
ohne fragil zu sein. Kein Streamlit, kein Netzwerk, keine echten Daten.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "lq-025-visual-preview-quickstart.md"
_README = _ROOT / "README.md"


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


def _readme() -> str:
    return _README.read_text(encoding="utf-8")


# 1: Quickstart-Doku existiert.
def test_quickstart_doc_exists():
    assert _DOC.is_file()


# 2: README enthält den Quickstart-Abschnitt.
def test_readme_has_quickstart_heading():
    assert "Visual Preview Quickstart" in _readme()


# 3: README enthält den Streamlit-Startbefehl.
def test_readme_has_streamlit_run():
    assert "streamlit run tools/visual_preview/app.py" in _readme()


# 4: README enthält den Fallback-/Modul-Aufruf.
def test_readme_has_module_fallback():
    assert "python -m tools.visual_preview.app" in _readme()


# 5: README enthält den optionalen Visual-Extra-Install.
def test_readme_has_visual_extra_install():
    assert 'pip install -e ".[visual]"' in _readme()


# 6: README enthält die Safety-Hinweise.
def test_readme_has_safety_notes():
    readme = _readme()
    assert "No live trading" in readme
    assert "No trading recommendation" in readme
    assert "No profitability assessment" in readme


# 7: Doku enthält die First-Run Checklist.
def test_doc_has_first_run_checklist():
    assert "First-Run Checklist" in _doc()


# 8: Doku enthält das Bid/Ask-Schema.
def test_doc_has_bid_ask_schema():
    assert "Bid/Ask CSV" in _doc()


# 9: Doku enthält das OHLCV-Schema.
def test_doc_has_ohlcv_schema():
    assert "OHLCV CSV" in _doc()


# 10: Doku enthält das OHLCV->bid/ask-Mapping.
def test_doc_has_mapping():
    doc = _doc()
    assert "close -> bid" in doc
    assert "mid = close" in doc


# 11: Doku enthält Troubleshooting.
def test_doc_has_troubleshooting():
    assert "Troubleshooting" in _doc()


# 12: Doku enthält Safety Boundaries.
def test_doc_has_safety_boundaries():
    assert "Safety Boundaries" in _doc()


# 13: keine verbotene Wertungssprache in README/Doku (fragment-gebaute Liste,
# damit diese Testdatei sich nicht selbst matcht). "recommendation" in
# "No trading recommendation" ist erlaubt und steht NICHT auf der Liste.
def test_no_forbidden_valuation_language():
    combined = (_doc() + _readme()).lower()
    forbidden = [
        "profit" + "able",
        "win" + "ner",
        "guar" + "anteed",
        "best " + "strategy",
        "should " + "trade",
    ]
    for token in forbidden:
        assert token not in combined, f"verbotener Wertungsbegriff: {token!r}"
