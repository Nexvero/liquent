from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-499-authorized-cleanup-revision-mutation-and-atomic-clearance-contract.md"


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_four_mutation_authorities_are_separate() -> None:
    text = _text()
    for heading in (
        "## Management-Lifecycle-Autorität", "## Hold-Autorität",
        "## Recovery-Autorität", "## Referenz-Autorität",
    ):
        assert heading in text
    assert "Eine gemeinsame generische Allowmutation ist ausgeschlossen" in text


def test_session_membership_and_cleanup_capability_do_not_self_authorize() -> None:
    text = _text()
    assert "SessionPrincipal" in text
    assert "trägt keine Authority" in text
    assert "Workspace-Membership und Researchpermissions reichen" in text
    assert "autorisiert nicht ihre eigene Vergabe oder" in text


def test_revisions_are_append_only_server_sequenced_and_retry_safe() -> None:
    text = _text()
    assert "Caller liefern keine autoritative Sequenznummer" in text
    assert "UPDATE, DELETE, Reorder und Überschreiben" in text
    assert "erwartete aktuelle Revisions-ID" in text
    assert "Ein Retry mit derselben Mutationsidentität und exakt demselben" in text
    assert "serverseitigen aware-UTC-Uhr" in text


def test_revocation_and_blocking_affect_later_clearance() -> None:
    text = _text()
    assert "Inactive und Blocked sind normale append-only Zustandsrevisionen" in text
    assert "jede spätere Clearanceentscheidung" in text
    assert "dürfen nicht wieder als\naktuell ausgewählt werden" in text


def test_clearance_is_internal_and_caller_evidence_is_rejected() -> None:
    text = _text()
    assert "Nur eine interne kontrollierte Composition" in text
    assert "Alle weiteren Fakten werden innerhalb der Composition serverseitig aufgelöst" in text
    assert "Caller-gelieferte Evidence-Dicts oder Allowflags" in text


def test_attempt_and_clearance_must_be_created_atomically() -> None:
    text = _text()
    assert "Attemptzeile und\nClearancezeile in derselben serialisierten Datenbanktransaktion" in text
    assert "Entweder beide Bindungen committen oder keine von beiden" in text
    assert "bereits separat persistierter Attempt ohne Clearance wird nicht" in text
    assert "eine neue nichtwiederverwendbare\nAttempt-ID erforderlich" in text


def test_all_current_system_of_record_facts_are_revalidated() -> None:
    text = _text()
    for fact in (
        "aktiven persistenten Actor", "aktiven Handoffscope",
        "Eligible-Retentionentscheidung", "Active-Managementrevision",
        "Clear-Holdrevision", "Clear-Recoveryrevision",
        "Clear-Referenzrevision", "vollständigen terminalen Journalview",
    ):
        assert fact in text
    assert "Kein vorab gelesener LQ-498-Snapshot" in text


def test_contract_distinguishes_absence_rejection_and_unavailability() -> None:
    text = _text()
    assert "## Neutrale Abwesenheit und Zurückweisung" in text
    assert "detailarm zurückgewiesen" in text
    assert "## Technische Unverfügbarkeit" in text
    assert "Der Vertrag benennt keinen neuen Exceptiontyp" in text


def test_no_implementation_or_physical_effect_is_opened() -> None:
    text = _text()
    assert "keine Domainklasse, Portsignatur, Tabelle, Migration, SQL" in text
    assert "keinen Grant-, Revoke-, Block-, Clear- oder Clearance-Schreibpfad" in text
    assert "Unlink, Rmdir und rekursiver Cleanup bleiben geschlossen" in text
    assert "`20260825_0036` und 36" in text


def test_roadmap_records_lq499_and_lq500() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-499 authorized cleanup revision mutation and atomic clearance contract:" in roadmap
    assert "lq-499-authorized-cleanup-revision-mutation-and-atomic-clearance-contract.md" in roadmap
    assert "nächster Slice LQ-500" in roadmap
