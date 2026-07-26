"""Strukturtests für LQ-055; keine Stack-Installation oder Runtime-Änderung."""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC_NAME = "lq-055-start-stack-technology-decision.md"
_DOC = _ROOT / "docs" / _DOC_NAME
_README = _ROOT / "README.md"
_ROADMAP = _ROOT / "docs" / "technical-status-and-roadmap.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_lq055_exists_and_is_linked():
    assert _DOC.is_file()
    assert _DOC_NAME in _read(_README)
    assert _DOC_NAME in _read(_ROADMAP)


def test_lq055_selects_complete_start_stack():
    doc = _read(_DOC)
    for term in (
        "Python + FastAPI + Uvicorn",
        "PostgreSQL 18",
        "TypeScript + React + Vite",
        "Docker Engine + Docker Compose",
        "Prometheus",
        "Grafana",
        "Restic zu OVHcloud",
        "GitHub Actions + GitHub Container Registry",
    ):
        assert term in doc


def test_lq055_avoids_extra_runtime_services_initially():
    doc = _read(_DOC)
    assert "Kein separater Message Broker in Slice 0/1" in doc
    assert "Redis wird ebenfalls nicht als Pflichtdienst eingeführt" in doc
    assert "kein Node-Prozess in Production" in doc


def test_lq055_preserves_research_core_boundary():
    doc = _read(_DOC)
    assert "src/liquent → keine Plattform-, HTTP- oder Persistenzabhängigkeit" in doc
    assert "Research-Kern bleibt importstabil und frameworkfrei" in doc


def test_lq055_has_versioning_and_secret_policy():
    doc = _read(_DOC)
    assert "committed Lockfiles" in doc
    assert "Containerimages werden in Production per Digest referenziert" in doc
    assert "Secrets erscheinen weder in Compose-Dateien" in doc


def test_lq055_keeps_trading_connectivity_out_of_scope():
    doc = _read(_DOC)
    assert "Keine Live-, Broker-, Exchange- oder produktive Paper-Funktion freigegeben" in doc
    assert "Keiner dieser Prozesse erhält Broker- oder Trading-Zugangsdaten" in doc


def test_lq055_defines_next_implementation_step():
    doc = _read(_DOC)
    assert "LQ-056 — Repository Foundation und Architecture Guardrails" in doc
