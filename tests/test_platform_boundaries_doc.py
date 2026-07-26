"""Strukturtests für LQ-053; keine Produktionslogik und kein Netzwerk."""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC_NAME = "lq-053-platform-boundaries-and-evolution.md"
_DOC = _ROOT / "docs" / _DOC_NAME
_README = _ROOT / "README.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_lq053_exists_and_is_linked():
    assert _DOC.is_file()
    assert _DOC_NAME in _text(_README)
    assert _DOC_NAME in _text(_ROADMAP)


def test_lq053_defines_required_boundaries():
    doc = _text(_DOC)
    for term in (
        "Verbindliche Produktgrenze",
        "Ist-Architektur des Repositorys",
        "Zielgrenzen des modularen Monolithen",
        "Gemeinsame Plattformobjekte",
        "Ausführungsgrenzen",
        "MVP-Neuschnitt",
        "Entscheidungstore vor Technik",
    ):
        assert term in doc


def test_lq053_preserves_safety_boundary():
    doc = _text(_DOC).lower()
    for term in (
        "keine versteckte oder autonome live-aktivierung",
        "keine brokerberechtigung zur auszahlung oder verwahrung",
        "keine kauf- oder verkaufsempfehlungen",
    ):
        assert term in doc


def test_lq053_defers_technology_selection():
    doc = _text(_DOC)
    assert "Keine Technologie-, Framework- oder Datenbankentscheidung" in doc
    assert "Erst danach folgen Entscheidungen" in doc


def test_lq053_keeps_product_ui_separate_from_preview():
    doc = _text(_DOC).lower()
    assert "eingefrorenes internes werkzeug; keine produkt-ui" in doc
