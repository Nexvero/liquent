"""Doku-Tests für den BacktestRunner Regression Test Plan (LQ-036 Phase 2).

Prüft die finalisierte Plan-Doku + README/Roadmap-Verlinkung, ohne fragil zu
sein. Kein Streamlit, kein Netzwerk, keine echten Daten, keine Codeänderung.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "lq-036-backtest-runner-regression-test-plan.md"
_README = _ROOT / "README.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"
_VP_INDEX = _ROOT / "docs" / "visual-preview-index.md"

_DOC_NAME = "lq-036-backtest-runner-regression-test-plan.md"


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


# 1: LQ-036-Doku existiert.
def test_spec_doc_exists():
    assert _DOC.is_file()


# 2-7: Doku enthält die Kern-/Verified-State-Abschnitte.
def test_doc_has_verified_state_sections():
    doc = _doc()
    for heading in (
        "Verified Current State",
        "BacktestRunner",
        "BacktestResult",
        "TradeResult",
        "RiskEngine",
        "CostModel / Metrics / Reporting",
    ):
        assert heading in doc, f"LQ-036-Doku fehlt Abschnitt: {heading!r}"


# 8-16: Doku enthält Regression Test Groups A-H.
def test_doc_has_regression_test_groups():
    doc = _doc()
    for heading in (
        "Regression Test Groups",
        "Group A",
        "Group B",
        "Group C",
        "Group D",
        "Group E",
        "Group F",
        "Group G",
        "Group H",
    ):
        assert heading in doc, f"LQ-036-Doku fehlt Gruppe/Abschnitt: {heading!r}"


# 17-20: Doku enthält Fixture-/Scope-/Safety-Abschnitte.
def test_doc_has_scope_and_safety_sections():
    doc = _doc()
    for heading in (
        "Synthetic Fixture Strategy",
        "Recommended Phase 3 / Later Scope",
        "Out of Scope",
        "Safety Boundaries",
    ):
        assert heading in doc, f"LQ-036-Doku fehlt Abschnitt: {heading!r}"


# Doku verankert verifizierte echte Identifier und KEINE falschen Feldnamen.
def test_doc_documents_real_identifiers():
    doc = _doc()
    for token in (
        "BacktestRunner",
        "BacktestResult",
        "TradeResult",
        "RiskEngine",
        "CostModel",
        "BacktestExperimentSummary",
        "ending_equity",
        "equity_curve",
        "entry_time",
        "exit_time",
        "quantity",
    ):
        assert token in doc, f"LQ-036-Doku fehlt verifizierter Bezeichner: {token!r}"


# 21: Roadmap verlinkt LQ-036.
def test_roadmap_links_plan():
    assert _DOC_NAME in _ROADMAP.read_text(encoding="utf-8")


# 22: README verlinkt LQ-036.
def test_readme_links_plan():
    assert _DOC_NAME in _README.read_text(encoding="utf-8")


# 23: Visual Preview Index enthält NICHT LQ-036 (Visual Preview bleibt frozen).
def test_visual_preview_index_has_no_lq036():
    assert _DOC_NAME not in _VP_INDEX.read_text(encoding="utf-8")
    assert "lq-036" not in _VP_INDEX.read_text(encoding="utf-8").lower()


def _roadmap_lq036_section() -> str:
    """Nur der BacktestRunner-/Trade-Lifecycle-Abschnitt (## 12. ...).

    Die Roadmap enthält an früherer Stelle (Reporting-Abschnitt) eine bestehende
    Meta-Disclaimer-Zeile (`kein Ranking/winner/...`); diese soll der
    Wertungs-Scan nicht fälschlich treffen, daher wird nur ab dem
    BacktestRunner-Abschnitt gescannt (enthält LQ-035 + LQ-036).
    """
    text = _ROADMAP.read_text(encoding="utf-8")
    marker = "## 12. BacktestRunner"
    return text[text.index(marker):] if marker in text else ""


# 24: keine verbotene Wertungssprache (fragment-gebaute Liste, damit diese
# Testdatei sich nicht selbst matcht). "recommendation"/"profitability" bleiben
# erlaubt (legitime „no ..."-Disclaimer); der Roadmap-Anteil ist auf den
# LQ-036/LQ-035-Abschnitt beschränkt (s. o.).
def test_no_forbidden_valuation_language():
    combined = (
        _doc()
        + _README.read_text(encoding="utf-8")
        + _roadmap_lq036_section()
    ).lower()
    forbidden = [
        "win" + "ner",
        "guar" + "anteed",
        "best " + "strategy",
        "should " + "trade",
    ]
    for token in forbidden:
        assert token not in combined, f"verbotener Wertungsbegriff: {token!r}"


# 25: keine echten CSV-/Screenshot-/Report-Artefakte im docs-Verzeichnis.
def test_no_real_artefacts_in_docs():
    docs = _ROOT / "docs"
    for pattern in ("*.csv", "*.png", "*.jpg", "*.jpeg", "*.pdf"):
        assert not list(docs.glob(pattern)), f"unerwartetes Artefakt: {pattern}"
