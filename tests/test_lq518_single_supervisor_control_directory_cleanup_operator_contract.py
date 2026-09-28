from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-518-owner-controlled-single-supervisor-control-directory-cleanup-operator-contract.md"


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_contract_has_two_explicit_single_target_commands() -> None:
    text = _text()
    assert "Befehle `execute` oder `reconcile`" in text
    assert "genau ein persistentes Control Directory" in text
    assert "Kein Aufruf darf beide Befehle nacheinander ausführen" in text


def test_contract_requires_four_private_file_inputs_without_fallback() -> None:
    text = _text()
    for value in (
        "Datenbank-URL-Datei", "Backendinstanz-ID-Datei",
        "Control-Root-Datei", "Requestdatei",
        "Modus `0400` oder `0600`", "keinen Environment-",
    ):
        assert value in text


def test_execute_request_is_minimal_and_attempt_is_internal() -> None:
    text = _text()
    section = text[text.index("## Execute-Request"):text.index("## Execute-Reihenfolge")]
    assert "`actor_user_id`" in section
    assert "`directory_id`" in section
    assert "enthält keine Attempt-ID" in section
    assert "kryptografisch starke neue Attempt-ID" in section
    assert "keine Rolle, Permission, Capability" in section
    assert "Allow-/Force-/Override-Boolean" in section


def test_principal_never_replaces_current_persistent_clearance() -> None:
    text = _text()
    assert "Principal ist keine Authority" in text
    assert "nicht als Allowentscheidung" in text
    assert "aktuell aus dem System of Record" in text
    assert "Clearance genau einmal erzeugen" in text
    assert "nur bei exakt gebundener positiver Clearance" in text


def test_execution_is_once_only_and_unknown_does_not_auto_reconcile() -> None:
    text = _text()
    assert "an höchstens einer Stelle und ohne Schleife" in text
    assert "keinen zweiten Preflight, Claim oder Remove" in text
    assert "`outcome=reconciliation_required`" in text
    assert "startet Reconciliation nicht automatisch" in text


def test_reconciliation_is_separate_read_only_single_call() -> None:
    text = _text()
    section = text[text.index("## Reconcile-Request"):text.index("## Technische Unverfügbarkeit")]
    assert "`attempt_id`" in section
    assert "`directory_id`" in section
    assert "enthält keinen Actor" in section
    assert "genau einmal auf" in section
    assert "Clearance-Erzeugung und Execution" in section
    assert "niemals\naufgerufen" in section


def test_contract_separates_closed_business_and_technical_outcomes() -> None:
    text = _text()
    for value in (
        "`outcome=removed`", "`outcome=already_absent`",
        "`outcome=not_available`", "`outcome=rejected`",
        "`outcome=absent`", "`outcome=present`", "`outcome=conflict`",
        "`operator_unavailable`",
    ):
        assert value in text
    assert "LQ-518 benennt keinen neuen domänenweiten Exceptiontyp" in text


def test_contract_forbids_discovery_batch_and_automatic_activation() -> None:
    text = _text()
    assert "keinen Lookup zum Auflisten oder Suchen" in text
    assert "keine Listenrequestform" in text
    assert "Queue, Cron-, Timer-" in text
    assert "weder von Appfactory noch Supervisorservice automatisch" in text


def test_roadmap_records_lq518_and_lq519() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-518 owner-controlled single supervisor control-directory cleanup operator contract:" in roadmap
    assert "lq-518-owner-controlled-single-supervisor-control-directory-cleanup-operator-contract.md" in roadmap
    assert "nächster Slice LQ-519" in roadmap
