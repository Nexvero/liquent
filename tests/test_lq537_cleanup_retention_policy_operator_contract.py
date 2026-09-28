from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-537-owner-controlled-supervisor-cleanup-retention-policy-operator-contract.md"


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_four_process_boundaries_are_fixed_and_separate() -> None:
    text = _text()
    for value in ("initialer Policy-/Authority-Bootstrap", "reguläre Policyänderung",
                  "regulärer Authority-Lifecycle", "Offline-Authority-Recovery"):
        assert value in text
    assert "Keine Grenze ruft eine andere implizit auf" in text
    assert "keine frei wählbare\n`action`" in text


def test_requests_are_closed_and_revision_generation_is_internal() -> None:
    text = _text()
    assert "Bootstrap-ID, Ziel-User-ID und positive" in text
    assert "Actor-User-ID, Change-ID, optionale" in text
    assert "genau `grant`, `deactivate` oder `reactivate`" in text
    assert "Recovery-ID, historisch bekannte Ziel-User-ID" in text
    assert "Policy- und Authorityrevisionen werden weiterhin intern erzeugt" in text


def test_principal_never_carries_authority_and_recovery_has_none() -> None:
    text = _text()
    assert "Actorprincipal ist Identität und keine caller-gelieferte Permitentscheidung" in text
    assert "Sie akzeptiert keinen Actor und erzeugt keinen `SessionPrincipal`" in text
    assert "Lockoutschutz und aktuelle Userfacts bleiben Adapterpflicht" in text


def test_private_inputs_and_outputs_are_owner_controlled() -> None:
    text = _text()
    assert "private Datenbank-URL-Datei" in text
    assert "ohne Symlinkfolge, owner-only,\nsingle-link, größenbegrenzt" in text
    assert "explizite private Ergebnisdatei" in text
    assert "owner-only, no-follow und atomar" in text
    assert "Environmentfallback" in text


def test_results_and_exit_codes_are_closed_detail_free() -> None:
    text = _text()
    assert "detailfreies `rejected`" in text
    assert "`operator_unavailable`" in text
    assert "`0` bezeichnet" in text and "`1` bezeichnet" in text and "`2` bezeichnet" in text
    assert "kein Ergebnis- oder Fehlerdetail" in text


def test_no_discovery_follow_on_or_runtime_effect() -> None:
    text = _text()
    assert "keinen Read-, Search-, Dump-, Diagnose- oder Repairmodus" in text
    assert "startet keine Evaluation, Decision" in text
    assert "keinen Operator, Entry Point, Parser" in text
    assert "63 Entry Points, 68 Operatormodule" in text
    assert "Head `20260826_0042`" in text


def test_roadmap_records_lq537_and_lq538() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-537 owner-controlled supervisor cleanup retention policy operator contract:" in roadmap
    assert "lq-537-owner-controlled-supervisor-cleanup-retention-policy-operator-contract.md" in roadmap
    assert "nächster Slice LQ-538" in roadmap
