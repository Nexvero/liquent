from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-509-physical-supervisor-control-directory-cleanup-execution-contract.md"


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_only_atomic_attempt_clearance_pair_opens_preparation() -> None:
    text = _text()
    assert "durch LQ-508 atomar erzeugten Paar" in text
    assert "Ein alleinstehender LQ-494-Attempt" in text
    assert "Cross-Attempt-, Cross-Actor-, Cross-Directory- und Cross-Revision-Adoption" in text


def test_principal_and_caller_facts_grant_no_authority() -> None:
    text = _text()
    assert "SessionPrincipal identifiziert nur den Actor" in text
    assert "trägt keine Cleanup-, Membership-, Research- oder Dateisystemauthority" in text
    assert "Caller-gelieferte Allowbooleans, Rollen, Capabilities, Pfade" in text


def test_current_authority_and_target_are_revalidated() -> None:
    text = _text()
    assert "vollständige aktuelle\nClearance erneut" in text
    assert "Management-, Retention-, Hold-, Recovery-, Referenz-, Registry-" in text
    assert "committierter Widerruf oder neuer Blocker" in text
    assert "vollständigen Retired-Wert" in text


def test_inventory_is_read_only_closed_and_descriptor_bound() -> None:
    text = _text()
    assert "## Unmittelbare read-only Inventur" in text
    assert "keine Datei anlegen, öffnen mit Schreibrecht, umbenennen" in text
    assert "kanonischen Control-Artefaktrollen" in text
    assert "Zusätzliche Hardlinks, unbekannte Namen, Unterdirectories" in text
    assert "Device und Inode" in text


def test_durable_distinct_write_claim_precedes_every_effect() -> None:
    text = _text()
    assert "dauerhaft und atomar aus `started` in einen eigenen Write-Claim-Zustand" in text
    assert "zwingend vor dem ersten möglicherweise wirksamen" in text
    assert "bestehende Zustand `outcome_unknown`" in text
    assert "nicht nachträglich als vorwirklicher Write-Claim" in text


def test_execution_is_exact_non_recursive_and_revalidated() -> None:
    text = _text()
    assert "bereits sicher geöffneten und\ngebundenen Root- und Leafdescriptoren" in text
    assert "Generisches rekursives Löschen, Globs, absolute Pfadmutation" in text
    assert "Unmittelbar vor jeder Namensmutation" in text
    assert "Parentdescriptor\ndauerhaft synchronisiert" in text


def test_success_requires_confirmed_absence_and_durable_root() -> None:
    text = _text()
    assert "`removed` darf erst nach bestätigter Entfernung" in text
    assert "bestätigter Abwesenheit des Leafs" in text
    assert "erfolgreicher Root-Synchronisierung" in text
    assert "einzelner Unlink ist noch kein\nCleanupabschluss" in text


def test_unknown_effect_is_reconciled_and_never_blindly_retried() -> None:
    text = _text()
    assert "nicht blind\nwiederholbaren, reconciliation-pflichtigen Ausgang" in text
    assert "niemals ein zweites\nMal starten" in text
    assert "rein lesender Reconciliation" in text
    assert "autorisiert keinen Retry desselben Attempts" in text


def test_absence_rejection_and_unavailability_remain_distinct() -> None:
    text = _text()
    assert "## Neutrale Abwesenheit und Zurückweisung" in text
    assert "detailarm zurückgewiesen" in text
    assert "## Technische Unverfügbarkeit" in text
    assert "Der Vertrag benennt keinen neuen Exceptiontyp" in text


def test_no_implementation_decision_and_next_slice_are_recorded() -> None:
    text = _text()
    assert "keine Domainklasse, Portsignatur, Tabelle, Migration, SQL" in text
    assert "Head bleibt `20260826_0039` mit 39" in text
    assert "LQ-510 sollte geschlossene Preflight-, Write-Claim-" in text


def test_roadmap_records_lq509_and_lq510() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-509 physical supervisor control-directory cleanup execution contract:" in roadmap
    assert "lq-509-physical-supervisor-control-directory-cleanup-execution-contract.md" in roadmap
    assert "nächster Slice LQ-510" in roadmap
