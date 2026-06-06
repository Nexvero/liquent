"""Doku-Tests für die BacktestRunner / Trade-Lifecycle Integration Spec (LQ-035).

Prüft die Spezifikations-Doku + README/Roadmap-Verlinkung, ohne fragil zu sein.
Kein Streamlit, kein Netzwerk, keine echten Daten, keine Codeänderung.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "lq-035-backtest-runner-trade-lifecycle-integration.md"
_README = _ROOT / "README.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"

_DOC_NAME = "lq-035-backtest-runner-trade-lifecycle-integration.md"


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


# 1: LQ-035-Doku existiert.
def test_spec_doc_exists():
    assert _DOC.is_file()


# 2-14: Doku enthält die Kernabschnitte.
def test_doc_has_core_sections():
    doc = _doc()
    for heading in (
        "Verified Current State",
        "Strategy Layer",
        "Runner Layer",
        "RiskEngine Layer",
        "CostModel / Metrics / Reporting",
        "Visual Preview",
        "Integration Gap",
        "Target Integration Model",
        "Trade-/Position-Lifecycle",
        "CostModel Integration",
        "Neutral Reporting Rules",
        "Recommended Phase 3 / Later Implementation Path",
        "Safety Boundaries",
    ):
        assert heading in doc, f"LQ-035-Doku fehlt Abschnitt: {heading!r}"


# Doku verankert verifizierte echte Identifier (nicht hypothetisch).
def test_doc_documents_real_identifiers():
    doc = _doc()
    for token in (
        "BacktestRunner",
        "BacktestResult",
        "RiskEngine",
        "CostModel",
        "TradeResult",
        "ending_equity",
        "equity_curve",
    ):
        assert token in doc, f"LQ-035-Doku fehlt verifizierter Bezeichner: {token!r}"


# 15: Roadmap verlinkt LQ-035.
def test_roadmap_links_spec():
    assert _DOC_NAME in _ROADMAP.read_text(encoding="utf-8")


# 16: README verlinkt LQ-035.
def test_readme_links_spec():
    assert _DOC_NAME in _README.read_text(encoding="utf-8")


def _roadmap_lq035_section() -> str:
    """Nur der von LQ-035 hinzugefügte Roadmap-Abschnitt (## 12. ...).

    Die Roadmap enthält an früherer Stelle eine bestehende Meta-Disclaimer-Zeile
    (`kein Ranking/winner/better/worse`); diese soll der Wertungs-Scan nicht
    fälschlich treffen, daher wird nur ab dem LQ-035-Abschnitt gescannt.
    """
    text = _ROADMAP.read_text(encoding="utf-8")
    marker = "## 12. BacktestRunner"
    return text[text.index(marker):] if marker in text else ""


# 17: keine verbotene Wertungssprache (fragment-gebaute Liste, damit diese
# Testdatei sich nicht selbst matcht). "recommendation" bleibt erlaubt; der
# Roadmap-Anteil ist auf den LQ-035-Abschnitt beschränkt (s. o.).
def test_no_forbidden_valuation_language():
    combined = (
        _doc()
        + _README.read_text(encoding="utf-8")
        + _roadmap_lq035_section()
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


# 18: keine echte CSV-Datei im docs-Verzeichnis.
def test_no_real_csv_files_in_docs():
    assert not list((_ROOT / "docs").glob("*.csv"))
