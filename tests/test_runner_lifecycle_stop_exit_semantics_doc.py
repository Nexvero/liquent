"""Doku-Tests für die Runner-Lifecycle-/Stop-Exit-Entscheidung (LQ-038 Phase 2).

Prüft die finalisierte Decision-Doku + README/Roadmap-Verlinkung, ohne fragil zu
sein. Kein Streamlit, kein Netzwerk, keine echten Daten, keine Codeänderung.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "lq-038-runner-lifecycle-stop-exit-semantics.md"
_README = _ROOT / "README.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"
_VP_INDEX = _ROOT / "docs" / "visual-preview-index.md"

_DOC_NAME = "lq-038-runner-lifecycle-stop-exit-semantics.md"


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


# 1: LQ-038-Doku existiert.
def test_spec_doc_exists():
    assert _DOC.is_file()


# 2-9: Doku enthält die Lifecycle-Abschnitte.
def test_doc_has_lifecycle_sections():
    doc = _doc()
    for heading in (
        "Verified Current Lifecycle",
        "Signal",
        "Risk Check",
        "Entry",
        "Exit",
        "Result",
    ):
        assert heading in doc, f"LQ-038-Doku fehlt Abschnitt: {heading!r}"


# 4: Doku enthält die echten Signal-Felder.
def test_doc_documents_real_signal_fields():
    doc = _doc()
    for field in ("timestamp", "direction", "strength", "metric", "stop_price"):
        assert field in doc, f"LQ-038-Doku fehlt Signal-Feld: {field!r}"


# 5: Doku weist explizit aus, dass Signal kein side-/price-Feld hat.
def test_doc_states_signal_has_no_side_or_price_field():
    doc = _doc().lower()
    assert "`signal`-`side`-feld" in doc, "Hinweis 'kein Signal-side-Feld' fehlt"
    assert "`signal`-`price`-feld" in doc, "Hinweis 'kein Signal-price-Feld' fehlt"


# 10-15: Doku enthält Decision Options A-E.
def test_doc_has_decision_options():
    doc = _doc()
    for heading in (
        "Decision Options",
        "Option A",
        "Option B",
        "Option C",
        "Option D",
        "Option E",
    ):
        assert heading in doc, f"LQ-038-Doku fehlt Option/Abschnitt: {heading!r}"


# 16-19: Doku enthält Decision-/Impact-/Test-/Safety-Abschnitte.
def test_doc_has_decision_impact_test_safety_sections():
    doc = _doc()
    for heading in (
        "Recommended Decision",
        "Impact Analysis",
        "Test Plan for Later Implementation",
        "Safety Boundaries",
    ):
        assert heading in doc, f"LQ-038-Doku fehlt Abschnitt: {heading!r}"


# Doku verankert verifizierte echte Identifier (kein erfundenes Feld).
def test_doc_documents_real_identifiers():
    doc = _doc()
    for token in (
        "BacktestRunner",
        "TradeResult",
        "RiskDecision",
        "entry_time",
        "exit_time",
        "quantity",
        "Close-to-Close",
        "sizing-only",
    ):
        assert token in doc, f"LQ-038-Doku fehlt verifizierter Bezeichner: {token!r}"


# 20: Roadmap verlinkt LQ-038.
def test_roadmap_links_doc():
    assert _DOC_NAME in _ROADMAP.read_text(encoding="utf-8")


# 21: README verlinkt LQ-038.
def test_readme_links_doc():
    assert _DOC_NAME in _README.read_text(encoding="utf-8")


# 22: Visual Preview Index enthält NICHT LQ-038.
def test_visual_preview_index_has_no_lq038():
    text = _VP_INDEX.read_text(encoding="utf-8").lower()
    assert _DOC_NAME not in text
    assert "lq-038" not in text


def _roadmap_backtest_section() -> str:
    """Nur der BacktestRunner-/Trade-Lifecycle-Abschnitt (## 12. ...).

    Die Roadmap enthält an früherer Stelle (Reporting-Abschnitt) eine bestehende
    Meta-Disclaimer-Zeile (`kein Ranking/winner/...`); diese soll der
    Wertungs-Scan nicht fälschlich treffen, daher wird nur ab dem
    BacktestRunner-Abschnitt gescannt (enthält LQ-035 … LQ-038).
    """
    text = _ROADMAP.read_text(encoding="utf-8")
    marker = "## 12. BacktestRunner"
    return text[text.index(marker):] if marker in text else ""


# 23: keine verbotene Wertungssprache (fragment-gebaute Liste, damit diese
# Testdatei sich nicht selbst matcht). "recommended decision"/"profitability"/
# "recommendation" bleiben erlaubt; der Roadmap-Anteil ist auf den
# BacktestRunner-Abschnitt beschränkt (s. o.).
def test_no_forbidden_valuation_language():
    combined = (
        _doc()
        + _README.read_text(encoding="utf-8")
        + _roadmap_backtest_section()
    ).lower()
    forbidden = [
        "win" + "ner",
        "guar" + "anteed",
        "best " + "strategy",
        "should " + "trade",
    ]
    for token in forbidden:
        assert token not in combined, f"verbotener Wertungsbegriff: {token!r}"


# 24: keine echten CSV-/Screenshot-/Report-Artefakte im docs-Verzeichnis.
def test_no_real_artefacts_in_docs():
    docs = _ROOT / "docs"
    for pattern in ("*.csv", "*.png", "*.jpg", "*.jpeg", "*.pdf"):
        assert not list(docs.glob(pattern)), f"unerwartetes Artefakt: {pattern}"
