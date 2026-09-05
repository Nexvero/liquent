from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-524-owner-controlled-supervisor-cleanup-authority-and-source-revision-operator-contract.md"


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_contract_keeps_four_authority_and_source_domains_separate() -> None:
    text = _text()
    for value in ("Management", "Hold", "Recovery", "Reference"):
        assert value in text
    assert "vier unabhängige Mengen" in text
    assert "getrennte append-only Revisionsquellen" in text
    assert "kein frei wählbares `source`" in text


def test_contract_separates_bootstrap_lifecycle_recovery_and_source_mutation() -> None:
    text = _text()
    for heading in (
        "## Authority-Bootstrap",
        "## Reguläre Authority-Mutation",
        "## Offline-Authority-Recovery",
        "## Quellrevisionsmutation",
    ):
        assert heading in text
    assert "Keine Grenze ruft eine andere implizit auf" in text


def test_principal_is_identity_and_current_authority_is_system_owned() -> None:
    text = _text()
    assert "`SessionPrincipal`; dieser Principal ist Identität und keine" in text
    assert "innerhalb der Mutation aus dem System of Record neu auf" in text
    assert "Caller-Behauptungen über Aktivität" in text
    assert "Es gibt keinen Authority-Cache" in text


def test_inputs_do_not_accept_allow_role_or_generic_source() -> None:
    text = _text()
    assert "kein caller-geliefertes `allow`, `eligible`, `authorized`" in text
    assert "allgemeine\nSupervisorberechtigung ersetzt keine" in text
    assert "Unbekannte Befehle und zusätzliche Felder" in text


def test_recovery_cannot_create_or_replace_members() -> None:
    text = _text()
    assert "vorhandene inaktive historische Person" in text
    assert "keine neue Person hinzufügen" in text
    assert "ohne `SessionPrincipal`" in text


def test_outcomes_are_closed_and_technical_unavailability_is_separate() -> None:
    text = _text()
    assert "gemeinsam als `rejected` ohne Detail" in text
    assert "`operator_unavailable`" in text
    assert "keine neue Exception" in text


def test_contract_opens_no_operator_schema_or_follow_on_effect() -> None:
    text = _text()
    assert "keinen Console Entry Point, Operatorcode" in text
    assert "keine Tabelle, Migration, SQL-, Domain-, Port-" in text
    assert "erzeugt keine Clearance" in text
    assert "Head bleibt `20260826_0040`" in text


def test_retention_reuse_and_next_slice_are_explicit() -> None:
    text = _text()
    assert "nicht als neue\nIdentitäten oder Operationen wiederverwendet" in text
    assert "weder Tabellenform noch konkrete Aufbewahrungsdauer" in text
    assert "LQ-525 implementiert zuerst die drei" in text
    assert "Retention, Retirement, Deployment" in text


def test_roadmap_records_lq524_and_lq525() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-524 owner-controlled supervisor cleanup authority and source revision operator contract:" in roadmap
    assert "lq-524-owner-controlled-supervisor-cleanup-authority-and-source-revision-operator-contract.md" in roadmap
    assert "nächster Slice LQ-525" in roadmap
