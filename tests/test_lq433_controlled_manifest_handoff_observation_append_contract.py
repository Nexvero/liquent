from pathlib import Path


ROOT = Path(__file__).parents[1]
CONTRACT = ROOT / "docs/lq-433-controlled-manifest-handoff-observation-append-contract.md"


def _text() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def test_untrusted_callers_cannot_supply_observation_facts() -> None:
    text = _text()
    required = (
        "keinen generischen Aufruf `append(attempt, kind, payload)`",
        "Observationkind oder Erfolgsboolean",
        "Sequenznummer oder aktuelle Registryrevision",
        "Digest oder Dateizahl",
        "Scope, Namen oder Actor als Override",
        "Jede Observationart benötigt eine intern kontrollierte quellenspezifische",
    )
    assert all(value in text for value in required)


def test_writer_start_retry_and_reconciliation_routing_are_closed() -> None:
    text = _text()
    assert "`writer_started` muss durable committed sein" in text
    assert "einen zweiten Writeraufruf" in text.replace("\n", " ")
    assert "Auch `manifest_absent` nach einem gestarteten Attempt" in text
    assert "folgt stattdessen eine frische\nLQ-427-Reconciliation" in text
    for outcome in (
        "`manifest_absent`",
        "`manifest_handed_off`",
        "`manifest_temporary_only`",
        "`manifest_handed_off_pending_cleanup`",
        "`manifest_handoff_conflict`",
    ):
        assert outcome in text


def test_result_recording_survives_revocation_without_new_authority() -> None:
    text = _text()
    assert "auch dann historiesicher angehängt werden können" in text
    assert "Ergebnisappend ist mechanische Evidenzsicherung" in text
    assert "keine neue fachliche Mutationsauthority" in text
    assert "darf aber die Sicherung eines bereits eingetretenen Ausgangs nicht" in text


def test_retry_sequence_failure_and_retention_are_fail_closed() -> None:
    text = _text()
    required = (
        "`ManifestHandoffObservationId` als technischen Retryanker",
        "niemals eine neue\nSequenz",
        "nächste Sequenznummer wird ausschließlich innerhalb der atomaren",
        "Stale Übergang, fehlendes Attempt oder unzulässiger Operationsstart",
        "detailfreie technische\nUnverfügbarkeit",
        "Observationen sind append-only",
        "Scope-/Name-Bindung überdauert weiterhin jede Observation- und",
    )
    assert all(value in text for value in required)


def test_roadmap_links_contract_without_implementation() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-433 controlled manifest handoff observation append contract:" in roadmap
    assert "`docs/lq-433-controlled-manifest-handoff-observation-append-contract.md`" in roadmap
    assert "nächster Slice LQ-434" in roadmap
    assert "LQ-433 ergänzt keinen Domain-Typ, Port, Adapter" in _text()
