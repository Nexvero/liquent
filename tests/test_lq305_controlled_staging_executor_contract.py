from pathlib import Path


ROOT = Path(__file__).parents[1]
DOCUMENT = ROOT / "docs/lq-305-controlled-research-worker-staging-executor-contract.md"


def _contract() -> str:
    return DOCUMENT.read_text(encoding="utf-8")


def test_contract_binds_explicit_single_run_authorization() -> None:
    contract = _contract()
    for required in (
        "owner-only Autorisierungsdatei", "opake Run-ID", "exakt `staging`",
        "Source-Commit", "Application-Image-Digest", "Compose-SHA-256",
        "Migration-Head", "UTC-Zeitfenster", "müssen verschieden sein",
        "caller-gelieferte Allow-Booleans",
    ):
        assert required in contract


def test_contract_has_fixed_fail_closed_phase_order() -> None:
    contract = _contract()
    phases = (
        "Image-Digest auflösen", "Compose ausschließlich", "effektive Mount-",
        "Staging-PostgreSQL", "Migration-Gate einmal", "mutationsfreien Idle-Pfad",
        "synthetischen Job", "Artifacthash", "Permission entziehen",
        "Idle-SIGTERM", "Evidence atomar finalisieren",
    )
    positions = [contract.index(phase) for phase in phases]
    assert positions == sorted(positions)
    assert "nicht übersprungen, umgeordnet, parallelisiert" in contract


def test_contract_bounds_mutation_unknown_outcome_and_cleanup() -> None:
    contract = _contract()
    for required in (
        "Mutationsbudget", "keine bestehende Datenbank", "niemals automatisch erneut",
        "Unknown Outcome", "fehlende Checks als `unavailable`",
        "Cleanup ist ein eigener späterer", "SIGKILL",
    ):
        assert required in contract


def test_contract_separates_redacted_evidence_from_approval() -> None:
    contract = _contract()
    for required in (
        "LQ-304-kompatibles JSON", "Evidence-Referenz", "atomar",
        "Raw stdout/stderr", "feste Argumentlisten ohne Shell",
        "Environment wird geschlossen allowlisted", "darf LQ-304 weder importieren",
        "keine Readinessentscheidung",
    ):
        assert required in contract


def test_slice_claims_no_implementation_or_external_effect() -> None:
    contract = _contract()
    for required in (
        "implementiert und startet noch keinen Executor", "keine Schema-",
        "keinen realen Imagepull", "Containerstart", "Datenbankzugriff",
        "LQ-306",
    ):
        assert required in contract
