"""Doku-Tests für die Runner-Lifecycle-Pause-/Implementation-Decision (LQ-040 Phase 2).

Prüft die finalisierte Decision-/Pause-Checkpoint-Doku + README/Roadmap-
Verlinkung, ohne fragil zu sein. Kein Streamlit, kein Netzwerk, keine echten
Daten, keine Codeänderung. Reine Doku-Tests — kein exit_reason/Stop-Exit gegen
Produktionscode.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "lq-040-runner-lifecycle-implementation-decision.md"
_README = _ROOT / "README.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"
_VP_INDEX = _ROOT / "docs" / "visual-preview-index.md"

_DOC_NAME = "lq-040-runner-lifecycle-implementation-decision.md"


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


# 1: LQ-040-Doku existiert.
def test_spec_doc_exists():
    assert _DOC.is_file()


# 2: Doku enthält Current Runner Lifecycle Contract.
def test_doc_has_current_runner_lifecycle_contract():
    assert "Current Runner Lifecycle Contract" in _doc()


# 3-7: Doku enthält Decision Options A-D.
def test_doc_has_decision_options():
    doc = _doc()
    for heading in (
        "Decision Options",
        "Option A",
        "Option B",
        "Option C",
        "Option D",
    ):
        assert heading in doc, f"LQ-040-Doku fehlt Option/Abschnitt: {heading!r}"


# 8-11: Doku enthält Decision-/Tracks-/Conditions-/Safety-Abschnitte.
def test_doc_has_decision_tracks_conditions_safety_sections():
    doc = _doc()
    for heading in (
        "Recommended Decision",
        "Possible Next Tracks",
        "Conditions Before Any exit_reason Implementation",
        "Safety Boundaries",
    ):
        assert heading in doc, f"LQ-040-Doku fehlt Abschnitt: {heading!r}"


# Doku verankert verifizierte echte Identifier + aktuellen Contract.
def test_doc_documents_real_identifiers_and_contract():
    doc = _doc()
    for token in (
        "BacktestRunner",
        "TradeResult",
        "RiskDecision",
        "Close-to-Close",
        "sizing-only",
        "exit_reason",
    ):
        assert token in doc, f"LQ-040-Doku fehlt verifizierter Bezeichner: {token!r}"


# 12: Roadmap verlinkt LQ-040.
def test_roadmap_links_doc():
    assert _DOC_NAME in _ROADMAP.read_text(encoding="utf-8")


# 13: README verlinkt LQ-040.
def test_readme_links_doc():
    assert _DOC_NAME in _README.read_text(encoding="utf-8")


# 14: Visual Preview Index enthält NICHT LQ-040.
def test_visual_preview_index_has_no_lq040():
    text = _VP_INDEX.read_text(encoding="utf-8").lower()
    assert _DOC_NAME not in text
    assert "lq-040" not in text


# 15: keine verbotene Wertungssprache in der LQ-040-Doku (fragment-gebaute Liste,
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


# 16: keine echten CSV-/Screenshot-/Report-Artefakte im docs-Verzeichnis.
def test_no_real_artefacts_in_docs():
    docs = _ROOT / "docs"
    for pattern in ("*.csv", "*.png", "*.jpg", "*.jpeg", "*.pdf"):
        assert not list(docs.glob(pattern)), f"unerwartetes Artefakt: {pattern}"
