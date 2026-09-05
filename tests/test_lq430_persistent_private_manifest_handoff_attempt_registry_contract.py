from pathlib import Path


ROOT = Path(__file__).parents[1]
CONTRACT = ROOT / "docs/lq-430-persistent-private-manifest-handoff-attempt-registry-contract.md"


def _text() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def test_stable_scope_attempt_and_name_non_reuse_are_explicit() -> None:
    text = _text()
    required = (
        "intern erzeugte stabile `RegistryScopeId`",
        "intern erzeugte stabile\n`HandoffAttemptId`",
        "nie erneut vergeben",
        "höchstens einer\n`HandoffAttemptId` zugeordnet",
        "Die erste erfolgreiche Reservierung beansprucht den Namen dauerhaft",
        "Es gibt kein Delete-and-recreate, Upsert, Rebind oder Namensrecycling",
    )
    assert all(value in text for value in required)


def test_registry_not_filesystem_is_non_reuse_system_of_record() -> None:
    text = _text()
    assert "normative System of Record" in text
    assert "Final-, Temp- oder sonstige Dateiabwesenheit ist dafür niemals autoritativ" in text
    assert "Abwesenheit ist eine Beobachtung, kein Rücksetzen auf unbenutzt" in text
    assert "Eine neue Attempt-ID für denselben Namen ist immer unzulässig" in text


def test_authority_atomicity_retry_and_failure_are_fail_closed() -> None:
    text = _text()
    required = (
        "vor jeder möglichen Writer-Dateisystemmutation\ndurable committed",
        "keinen caller-supplied Allow-Boolean",
        "Fehlender, inaktiver oder nicht zum Scope gebundener Actor scheitert\nfail-closed",
        "atomar committen oder vollständig\nausbleiben",
        "Technischer Retry darf nur dieselbe `HandoffAttemptId`",
        "detailfreie technische\nUnverfügbarkeit",
    )
    assert all(value in text for value in required)


def test_retention_and_non_implementation_bounds_are_explicit() -> None:
    text = _text()
    assert "gesamte\nLebensdauer des Registry-Namensraums" in text
    assert "überdauert die Dateievidenz" in text
    assert "keine konkrete Frist, Tabelle, Archivstufe" in text
    assert "keine Datei, Tabelle, Spalte, SQL-Anweisung, Migration" in text
    assert "keinen Adapter, Operator, CLI, Route" in text
    assert "importiert bestehende Dateien nicht automatisch" in text


def test_roadmap_links_contract_and_next_slice() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-430 persistent private manifest handoff attempt registry contract:" in roadmap
    assert "`docs/lq-430-persistent-private-manifest-handoff-attempt-registry-contract.md`" in roadmap
    assert "nächster Slice LQ-431" in roadmap
