from pathlib import Path


ROOT = Path(__file__).parents[1]
CONTRACT = ROOT / "docs/lq-440-manifest-handoff-execution-ownership-and-recovery-contract.md"


def test_contract_requires_claim_before_start_and_one_execution_owner() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "vor `writer_started` erwerben" in text
    assert "höchstens ein Execution-Claim den Writerstart gewinnen" in text
    assert "Nur der Prozess, dem dieser aktive Claim persistent gehört" in text
    assert "PID-Datei, Lockfile oder Dateiabwesenheit genügen\nnicht" in text


def test_lease_expiry_never_proves_process_end_or_authorizes_recovery() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "Lease-Ablauf ist kein Prozessende" in text
    assert "Zeitablauf allein weder Claimübernahme, Reconciliation,\nCleanup" in text
    assert "keine theoretische Fencingwirkung" in text
    assert "fence-fähiger Writer wäre ein separater Architekturwechsel" in text


def test_terminal_process_evidence_is_direct_and_not_caller_boolean() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "direkten kontrollierten Prozessgrenze" in text
    assert "Caller-Boolean `process_ended`" in text
    assert "Timeout, fehlender PID-Eintrag, Logtext\noder Heartbeatverlust" in text
    assert "Ohne diesen Nachweis bleibt das Attempt fail-closed blockiert" in text


def test_recovery_is_separate_authorized_and_read_only() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "separaten intern erzeugten stabilen Recovery-Claim" in text
    assert "explizite\nscopegebundene Manifest-Handoff-Recoveryfähigkeit" in text
    assert "SessionPrincipal identifiziert nur den Actor" in text
    assert "Recovery ruft ausschließlich den LQ-427-Reconciler" in text
    assert "Sie ruft niemals LQ-426 auf" in text
    assert "Cleanup bleibt selbst bei pending-cleanup außerhalb" in text


def test_contract_keeps_revocation_retries_and_outcomes_fail_closed() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "Entzug vor Erwerb des Recovery-Claims verhindert" in text
    assert "Jede spätere Entscheidung liest aktuelle Aktivität" in text
    assert "derselben Observation-ID und denselben Fakten\nwiederholt" in text
    assert "Weder Reconciler noch Writer werden wegen eines unklaren Appendcommits" in text
    assert "Neutrale Ablehnung" in text
    assert "Detailfreie technische Unverfügbarkeit" in text


def test_contract_preserves_retention_existing_attempts_and_revision() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "werden nie für\nandere Prozesse oder Attempts wiederverwendet" in text
    assert "Attempts ohne Execution-Claim dürfen nicht automatisch" in text
    assert "Bestandsverankerung bleibt ein eigener Slice" in text
    assert "keine Tabelle, Spalte, SQL-Anweisung, Migration" in text
    assert "Revision und Head bleiben `20260819_0028`" in text


def test_roadmap_records_contract_and_next_slice() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-440 manifest handoff execution ownership and recovery contract:" in roadmap
    assert "`docs/lq-440-manifest-handoff-execution-ownership-and-recovery-contract.md`" in roadmap
    assert "nächster Slice LQ-441" in roadmap
