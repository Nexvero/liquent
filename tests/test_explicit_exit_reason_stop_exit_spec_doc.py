"""Doku-Tests für die Explicit-Exit-Reason-/Stop-Exit-Spezifikation (LQ-039 Phase 2).

Prüft die finalisierte Spezifikations-Doku + README/Roadmap-Verlinkung, ohne
fragil zu sein. Kein Streamlit, kein Netzwerk, keine echten Daten, keine
Codeänderung. Reine Doku-Tests — kein exit_reason/Stop-Exit gegen
Produktionscode.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "lq-039-explicit-exit-reason-stop-exit-spec.md"
_README = _ROOT / "README.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"
_VP_INDEX = _ROOT / "docs" / "visual-preview-index.md"

_DOC_NAME = "lq-039-explicit-exit-reason-stop-exit-spec.md"


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


# 1: LQ-039-Doku existiert.
def test_spec_doc_exists():
    assert _DOC.is_file()


# 2: Doku enthält Verified Current Model.
def test_doc_has_verified_current_model():
    assert "Verified Current Model" in _doc()


# 3: Doku enthält Proposed Exit Reason Model.
def test_doc_has_proposed_exit_reason_model():
    assert "Proposed Exit Reason Model" in _doc()


# 4-6: Doku enthält die exit_reason-Werte close_to_close, stop_exit, end_of_data.
def test_doc_has_exit_reason_values():
    doc = _doc()
    for value in ("close_to_close", "stop_exit", "end_of_data"):
        assert value in doc, f"LQ-039-Doku fehlt exit_reason-Wert: {value!r}"


# 7: Doku enthält Stop-Exit Semantics Proposal.
def test_doc_has_stop_exit_semantics_proposal():
    assert "Stop-Exit Semantics Proposal" in _doc()


# 8-10: Doku enthält Long, Short, Same-bar vs next-bar.
def test_doc_has_long_short_same_vs_next_bar():
    doc = _doc()
    for heading in ("Long", "Short", "Same-bar vs next-bar"):
        assert heading in doc, f"LQ-039-Doku fehlt Abschnitt: {heading!r}"


# 11-16: Doku enthält Impact-/Plan-/Decision-/Safety-Abschnitte.
def test_doc_has_impact_plan_decision_safety_sections():
    doc = _doc()
    for heading in (
        "Data Model Impact",
        "Runner Impact",
        "Metrics / Reporting / CLI Impact",
        "Test Plan Before Implementation",
        "Recommended Decision",
        "Safety Boundaries",
    ):
        assert heading in doc, f"LQ-039-Doku fehlt Abschnitt: {heading!r}"


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
        assert token in doc, f"LQ-039-Doku fehlt verifizierter Bezeichner: {token!r}"


# Doku weist explizit aus, dass Signal kein side-/price-Feld hat.
def test_doc_states_signal_has_no_side_or_price_field():
    doc = _doc().lower()
    assert "kein `side`-feld" in doc, "Hinweis 'kein Signal-side-Feld' fehlt"
    assert "kein `price`-feld" in doc, "Hinweis 'kein Signal-price-Feld' fehlt"


# 17: Roadmap verlinkt LQ-039.
def test_roadmap_links_doc():
    assert _DOC_NAME in _ROADMAP.read_text(encoding="utf-8")


# 18: README verlinkt LQ-039.
def test_readme_links_doc():
    assert _DOC_NAME in _README.read_text(encoding="utf-8")


# 19: Visual Preview Index enthält NICHT LQ-039.
def test_visual_preview_index_has_no_lq039():
    text = _VP_INDEX.read_text(encoding="utf-8").lower()
    assert _DOC_NAME not in text
    assert "lq-039" not in text


# 20: keine verbotene Wertungssprache in der LQ-039-Doku (fragment-gebaute Liste,
# damit diese Testdatei sich nicht selbst matcht). "recommended decision",
# "profitability assessment", "trading recommendation", "performance", "equity"
# bleiben in ihren legitimen technischen Kontexten erlaubt.
def test_no_forbidden_valuation_language():
    doc = _doc().lower()
    forbidden = [
        "win" + "ner",
        "guar" + "anteed",
        "best " + "strategy",
        "should " + "trade",
    ]
    for token in forbidden:
        assert token not in doc, f"verbotener Wertungsbegriff: {token!r}"


# 21: keine echten CSV-/Screenshot-/Report-Artefakte im docs-Verzeichnis.
def test_no_real_artefacts_in_docs():
    docs = _ROOT / "docs"
    for pattern in ("*.csv", "*.png", "*.jpg", "*.jpeg", "*.pdf"):
        assert not list(docs.glob(pattern)), f"unerwartetes Artefakt: {pattern}"
