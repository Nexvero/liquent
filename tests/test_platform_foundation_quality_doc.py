"""Strukturtests für LQ-054; keine Runtime-, Netzwerk- oder VPS-Änderung."""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC_NAME = "lq-054-platform-foundation-quality-and-operations.md"
_DOC = _ROOT / "docs" / _DOC_NAME
_README = _ROOT / "README.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_lq054_exists_and_is_linked():
    assert _DOC.is_file()
    assert _DOC_NAME in _read(_README)
    assert _DOC_NAME in _read(_ROADMAP)


def test_lq054_defines_operational_quality_areas():
    doc = _read(_DOC)
    for heading in (
        "Service Level Objectives",
        "Health- und Readiness-Modell",
        "Deployment- und Releaseanforderungen",
        "Backup, Restore und Recovery",
        "Observability und Audit",
        "Kapazitäts- und Ressourcengrenzen",
        "Go-Live-Gates für Slice 0",
    ):
        assert heading in doc


def test_lq054_contains_measurable_recovery_and_capacity_targets():
    doc = _read(_DOC)
    for term in (
        "99,5 %",
        "Ziel-RPO",
        "Ziel-RTO",
        "30 % RAM",
        "Disk-Warnung bei 70 %",
        "Rollback innerhalb des Zielwerts getestet",
    ):
        assert term in doc


def test_lq054_keeps_health_and_readiness_separate():
    doc = _read(_DOC)
    assert "Health beantwortet, ob ein Prozess lebt" in doc
    assert "Readiness beantwortet, ob er sicher" in doc


def test_lq054_does_not_select_technology_or_enable_trading():
    doc = _read(_DOC)
    assert "Keine Programmiersprache, kein Framework und keine Datenbank ausgewählt" in doc
    assert "keine Live- oder Brokerfunktion freigeben" in doc


def test_lq054_requires_offsite_backup_and_restore_test():
    doc = _read(_DOC)
    assert "Backups liegen verschlüsselt außerhalb des VPS" in doc
    assert "vollständiger Restore-Test" in doc
