from pathlib import Path


ROOT = Path(__file__).parents[1]
CONTRACT = ROOT / "docs/lq-445-controlled-manifest-handoff-supervisor-contract.md"


def test_contract_has_fixed_separate_capabilities_without_free_command() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "genau einen LQ-426-Writerprozess" in text
    assert "genau einen LQ-427-Reconciliationprozess" in text
    assert "keinen generischen `run(command, args, env)`-Port" in text
    assert "weder ausführbaren Pfad, Modulnamen, Shellstring" in text
    assert "Cleanup, Shell, Build, Git und Deployment" in text


def test_writer_is_start_gated_until_durable_claimed_start() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "noch keinen\nSource- oder Zielzugriff ausführen kann" in text
    assert "`start_claimed_execution` mit Claim, Owner und Observation-ID durable" in text
    assert "erst danach das Gate genau einmal freigeben" in text
    assert "Start-Gate muss vor jedem möglichen Writercode wirksam sein" in text


def test_process_end_requires_direct_terminal_evidence_not_time_or_pid() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "Das Senden eines Signals allein ist kein Endnachweis" in text
    assert "Timeout allein erzeugt weder `start_not_confirmed`" in text
    assert "fehlende PID, nicht antwortender Prozess" in text
    assert "Kann Ende nicht belegt werden, bleibt der Claim aktiv" in text
    assert "PID-Reuse" in text


def test_controller_loss_and_one_start_are_fail_closed() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "nach\nControllerneustart eindeutig terminal oder weiterhin wirkend beobachten" in text
    assert "Ein unklarer Supervisorstart wird niemals durch einen zweiten Start" in text
    assert "Freigabe ist keine wiederholbare Retryoperation" in text
    assert "Writer wird niemals erneut gestartet" in text


def test_recovery_is_fresh_read_only_and_claim_bound() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "startgesperrten Reconciliationprozess genau einmal" in text
    assert "fünf\nLQ-444-Appendmethoden" in text
    assert "Reconciler wird wegen Commitunsicherheit nicht erneut ausgeführt" in text
    assert "Writer und Cleanup bleiben verboten" in text
    assert "Pending-cleanup bleibt ein beobachtetes Resultat" in text


def test_contract_keeps_authority_errors_retention_and_revision_separate() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "Supervisor akzeptiert keine Authorityparameter" in text
    assert "Neutrale Ablehnung" in text
    assert "Detailfreie technische Unverfügbarkeit" in text
    assert "Bestandsverankerung benötigt weiterhin" in text
    assert "Revision und Head bleiben `20260824_0029`" in text
    assert "keine neue Tabelle, Spalte, Migration, Domainklasse" in text


def test_roadmap_records_contract_and_next_slice() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-445 controlled manifest handoff supervisor contract:" in roadmap
    assert "`docs/lq-445-controlled-manifest-handoff-supervisor-contract.md`" in roadmap
    assert "nächster Slice LQ-446" in roadmap
