from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-495-current-supervisor-control-directory-cleanup-clearance-resolution-contract.md"


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_target_is_derived_directory_retired_handle_journal_scope() -> None:
    text = _text()
    order = [
        "Directory als Startpunkt", "Directory zu Handle", "Handle zu Journal",
        "Terminaler Journalfakt", "Journal zu Handoffscope",
    ]
    positions = [text.index(value) for value in order]
    assert positions == sorted(positions)
    assert "journal.registration.process_request.binding.scope_id" in text


def test_cleanup_management_is_separate_from_all_existing_capabilities() -> None:
    text = _text()
    for section in (
        "Eigene Cleanupmanagementfähigkeit", "Bestehende Registryauthority reicht nicht",
        "Membership und Research reichen nicht", "Onboardingmanagement reicht nicht",
    ):
        assert section in text
    assert "research:read" in text and "research:write" in text


def test_current_retention_policy_hold_recovery_and_references_are_all_required() -> None:
    text = _text()
    for section in (
        "Aktuelle Retentionentscheidung", "Policyrevision", "Holdquelle",
        "Recoveryquelle", "Referenzquelle", "Artefaktklassenspezifische Freigabe",
    ):
        assert section in text
    assert "höchste vollständige LQ-494-Decision" in text
    assert "ältere Eligible-Decision" in text


def test_attempt_start_requires_atomic_revision_binding_not_snapshot_or_cache() -> None:
    text = _text()
    assert "Atomare Bindungsanforderung" in text
    assert "serialisierbaren Entscheidung" in text
    assert "stabile revisionsgebundene Entscheidungen" in text
    assert "caller-geliefertes Snapshotobjekt" in text


def test_revision_0035_gap_keeps_production_closed() -> None:
    text = _text()
    assert "Lücke in Revision 0035" in text
    assert "noch keine Cleanupmanagement-, Hold-, Recovery- oder Referenzrevision" in text
    assert "reicht `start_cleanup_attempt` aus LQ-494 allein nicht" in text
    assert "additive Clearancefoundation erforderlich" in text


def test_revocation_blocks_new_or_pending_effect_but_not_result_reconstruction() -> None:
    text = _text()
    for section in (
        "Widerruf vor Attemptstart", "Widerruf nach Started vor Wirkung",
        "Widerruf während einer Mutationsfolge", "Exact Retry ohne neue Wirkung",
    ):
        assert section in text
    assert "Completed- oder Reconciled-Ergebnisse" in text


def test_unknown_allows_only_read_only_reconciliation_and_new_effect_needs_new_attempt() -> None:
    text = _text()
    assert "Outcome Unknown" in text
    assert "ausschließlich read-only Reconciliation" in text
    assert "Reconciliation Present" in text
    assert "neuen Attempt und vollständig neue" in text
    assert "Reconciliation Absent" in text


def test_absence_rejection_and_technical_unavailability_are_distinct_and_detail_free() -> None:
    text = _text()
    for section in ("Neutrale Abwesenheit", "Fachliche Ablehnung", "Technische Unverfügbarkeit"):
        assert section in text
    assert "einheitlich detailfrei abgelehnt" in text
    assert "davon getrennte detailfreie technische Unverfügbarkeit" in text


def test_contract_adds_no_implementation_schema_file_or_wiring() -> None:
    text = _text()
    assert "Keine Implementation" in text
    assert "keine Klasse, Domainwerte, Ports, Tabelle, SQL, Migration" in text
    assert "Head bleibt `20260825_0035`" in text
    assert "Productioncleanup bleibt geschlossen" in text


def test_roadmap_records_lq495_and_lq496() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-495 current supervisor control-directory cleanup clearance resolution contract:" in roadmap
    assert "lq-495-current-supervisor-control-directory-cleanup-clearance-resolution-contract.md" in roadmap
    assert "nächster Slice LQ-496" in roadmap
