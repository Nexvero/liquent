"""Doku-/Link-Tests für die Domain-Model-Hardening-Doku (LQ-047 Phase 2).

Prüft die finalisierte Doku + README/Roadmap-Verlinkung, ohne fragil zu sein.
Kein Streamlit, kein Netzwerk, keine echten Daten, keine Codeänderung. Importiert
keine Produktionslogik und erzeugt keine Artefakte.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "lq-047-domain-model-hardening.md"
_README = _ROOT / "README.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"
_VP_INDEX = _ROOT / "docs" / "visual-preview-index.md"

_DOC_NAME = "lq-047-domain-model-hardening.md"


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


# 1: LQ-047-Doku existiert.
def test_spec_doc_exists():
    assert _DOC.is_file()


# 2: Doku enthält die zentralen Abschnitte.
def test_doc_has_core_sections():
    doc = _doc()
    for heading in (
        "Status",
        "Purpose",
        "Verified Current Domain Model",
        "Behavior Locks",
        "Compatibility",
        "Safety Boundaries",
        "README/Roadmap Impact",
        "Phase 2 Implementation Status",
        "Non-Goals",
        "Deferred Topics",
    ):
        assert heading in doc, f"LQ-047-Doku fehlt Abschnitt: {heading!r}"


# 3: Doku verankert die verifizierten Domain-Entitäten.
def test_doc_documents_domain_entities():
    doc = _doc()
    for token in (
        "Direction",
        "PositionStatus",
        "Instrument",
        "MarketData",
        "OrderBookLevel",
        "OrderBookSnapshot",
        "LiquidityMetric",
        "Signal",
        "RiskDecision",
        "Position",
        "Experiment",
    ):
        assert token in doc, f"LQ-047-Doku fehlt Domain-Entität: {token!r}"


# 4: Doku verankert verifizierte Eigenschaften (frozen / default_factory / stop_price).
def test_doc_documents_verified_properties():
    doc = _doc()
    for token in ("frozen=True", "default_factory", "stop_price", "FrozenInstanceError"):
        assert token in doc, f"LQ-047-Doku fehlt Eigenschaft: {token!r}"


# 5: README verlinkt LQ-047.
def test_readme_links_doc():
    assert _DOC_NAME in _README.read_text(encoding="utf-8")


# 6: Roadmap verlinkt LQ-047.
def test_roadmap_links_doc():
    assert _DOC_NAME in _ROADMAP.read_text(encoding="utf-8")


# 7: Visual Preview Index enthält NICHT LQ-047.
def test_visual_preview_index_has_no_lq047():
    text = _VP_INDEX.read_text(encoding="utf-8").lower()
    assert _DOC_NAME not in text
    assert "lq-047" not in text


# 8: keine verbotene Wertungssprache in der LQ-047-Doku (fragment-gebaute Liste,
# damit diese Testdatei sich nicht selbst matcht). Achtung: die deutsche Vokabel
# "Gewinner" enthielte "winner" — die Doku vermeidet sie bewusst.
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


# 9: Doku benennt ausdrücklich, dass keine Produktionslogik geändert wurde.
def test_doc_states_no_production_logic_change():
    assert "Keine Produktionslogik geändert" in _doc() or "keine Produktionslogik geändert" in _doc()


# 10: keine echten CSV-/Screenshot-/Report-Artefakte im docs-Verzeichnis.
def test_no_real_artefacts_in_docs():
    docs = _ROOT / "docs"
    for pattern in ("*.csv", "*.png", "*.jpg", "*.jpeg", "*.pdf"):
        assert not list(docs.glob(pattern)), f"unerwartetes Artefakt: {pattern}"
