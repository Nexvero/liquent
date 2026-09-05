from pathlib import Path
import re


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-522-supervisor-control-directory-cleanup-end-to-end-readiness-audit.md"


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_audit_records_implemented_security_chain_without_false_readiness() -> None:
    text = _text()
    for value in (
        "Implementierte persistente Basis", "Implementierte Authoritytrennung",
        "Implementierte atomare Clearance", "Implementierte physische Sicherheit",
        "Implementierte Exactly-once-Grenze", "Implementierte Reconciliation",
        "Implementiertes explizites Opt-in",
    ):
        assert value in text
    assert "nicht für Productionbetrieb" in text
    assert "nicht als ausgeführter\nProductionnachweis" in text


def test_postgresql_sources_are_not_misreported_as_executed_evidence() -> None:
    text = _text()
    assert "Blocker 1 — PostgreSQL-Evidence fehlt" in text
    assert "wurden LQ-520 und LQ-521 nicht" in text
    assert "`LIQUENT_TEST_DATABASE_URL`" in text
    assert "keine neue commitgebundene `verification.json`" in text


def test_upstream_supervisor_and_retirement_wiring_remain_absent() -> None:
    text = _text()
    assert "Blocker 2 — Supervisor-Production-Wiring bleibt offen" in text
    assert "LQ-483-Blocker" in text
    assert "Blocker 3 — Retirement ist operativ nicht erreichbar" in text
    automatic_wiring = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            ROOT / "src/liquent_platform/transport/http/app.py",
            ROOT / "src/liquent_platform/transport/http/main.py",
        )
    )
    assert "manifest_handoff_supervisor_control_directory_retirement" not in automatic_wiring
    assert "liquent-supervisor-control-directory-retire" in (
        ROOT / "pyproject.toml"
    ).read_text(encoding="utf-8")


def test_historical_audit_and_current_remaining_operator_gaps_are_distinct() -> None:
    text = _text()
    assert "Blocker 4 — Retention-Eligibility hat keinen Operator" in text
    assert "Blocker 5 — Vier Authority-Sets sind nicht operationalisiert" in text
    assert "Blocker 6 — Quellrevisionen sind nicht operationalisiert" in text
    operators = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "src/liquent_platform/operators").glob("*.py")
    )
    assert "DatabaseManifestHandoffSupervisorCleanupMutationAuthorities" in operators
    assert "DatabaseManifestHandoffSupervisorCleanupRevisionMutations" in operators
    assert "record_cleanup_decision" not in operators


def test_private_configuration_and_incident_handoff_are_open() -> None:
    text = _text()
    assert "Blocker 7 — Technische Konfiguration ist nicht übergeben" in text
    assert "Blocker 8 — Incident-Handoff ist nicht durable" in text
    runbooks = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "operations/runbooks").glob("*.md")
    )
    assert "supervisor-control-directory-cleanup" not in runbooks


def test_release_inventory_drift_is_exact_and_fail_closed() -> None:
    text = _text()
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    bundle = (ROOT / "tools/operational_release_bundle.py").read_text(encoding="utf-8")
    entry_points = re.findall(r"^liquent-[a-z0-9-]+\s*=", project, re.MULTILINE)
    operators = list((ROOT / "src/liquent_platform/operators").glob("*.py"))
    assert len(entry_points) == 71
    assert len(operators) == 71
    assert "EXPECTED_ENTRY_POINT_COUNT = 71" in bundle
    assert "EXPECTED_OPERATOR_FILE_COUNT = 71" in bundle
    assert "Blocker 9 — Releaseinventar ist inkonsistent" in text
    assert "59 `liquent-*`-Entry-Points und 66" in text


def test_audit_does_not_open_automation_or_http_as_a_fix() -> None:
    text = _text()
    assert "Kein Blocker — fehlende Automatik" in text
    assert "Kein Blocker — fehlende HTTP-Route" in text
    assert "dürfen nicht als schnelle Blockerbehebung" in text


def test_safe_order_starts_with_inventory_then_operational_authority() -> None:
    text = _text()
    section = text[text.index("## Sichere Restreihenfolge"):text.index("## Aktuelle Freigabeentscheidung")]
    inventory = section.index("Releaseinventar")
    authority = section.index("Authority-Set-")
    deployment = section.index("Deployment-/Runbookübergabe")
    evidence = section.index("PostgreSQL-Gesamtlauf")
    assert inventory < authority < deployment < evidence


def test_roadmap_records_lq522_and_lq523() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-522 supervisor control-directory cleanup end-to-end readiness audit:" in roadmap
    assert "lq-522-supervisor-control-directory-cleanup-end-to-end-readiness-audit.md" in roadmap
    assert "nächster Slice LQ-523" in roadmap
