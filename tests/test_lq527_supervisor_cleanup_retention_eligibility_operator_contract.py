from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-527-owner-controlled-supervisor-cleanup-retention-eligibility-operator-contract.md"


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_request_contains_only_operation_and_directory_identity() -> None:
    text = _text()
    assert "ausschließlich eine stabile Operation-ID und eine interne" in text
    assert "Die Operation-ID ist keine Decision-ID" in text
    assert "weder Retired-Wert noch Handle, Leaf, Root, Pfad" in text


def test_caller_cannot_supply_disposition_policy_or_local_ttl() -> None:
    text = _text()
    assert "kein `eligible`, `retain`, `disposition`" in text
    assert "keine caller-gelieferte Policyrevision" in text
    assert "keine eingebaute Defaultfrist" in text
    assert "nicht lediglich `now - retired_at`, mtime" in text


def test_policy_and_target_are_resolved_from_systems_of_record() -> None:
    text = _text()
    assert "aktuell wirksame Retentionpolicy" in text
    assert "aus der persistenten Registry auf" in text
    assert "vollständig rekonstruierter, unverändert gebundener Retired-Wert" in text
    assert "Unbekannte Directory-ID ist neutrale Abwesenheit" in text


def test_evaluation_is_closed_current_and_not_cleanup_authority() -> None:
    text = _text()
    assert "ausschließlich `retain` oder `eligible`" in text
    assert "Ein späterer Policywechsel muss" in text
    assert "`eligible` ist nur ein Retentionfakt" in text
    assert "weiterhin separat revalidiert" in text


def test_operation_binding_and_result_handoff_must_survive_crash() -> None:
    text = _text()
    assert "dauerhafte\nnichtwiederverwendbare Bindung" in text
    assert "bestehende Decision-ID-Idempotenz allein genügt nicht" in text
    assert "Crash nach Decisionappend" in text
    assert "ersetzt aber nicht die persistente Operationbindung" in text


def test_results_separate_retained_rejected_and_unavailable() -> None:
    text = _text()
    assert "autoritative `retain`-Evaluation ist erfolgreicher Decisionappend" in text
    assert "detailfrei als `rejected`" in text
    assert "`operator_unavailable`" in text
    assert "keinen neuen Exceptiontyp" in text


def test_contract_opens_no_follow_on_or_runtime_effect() -> None:
    text = _text()
    assert "startet keine Clearance, keinen\nCleanup-Attempt" in text
    assert "retirert kein Directory" in text
    assert "keinen Entry Point, Operator, Policyadapter" in text
    assert "Head bleibt `20260826_0040`" in text


def test_next_slice_adds_values_port_and_operation_binding_first() -> None:
    text = _text()
    assert "LQ-528 definiert die geschlossenen Retention-Policy-Evaluationswerte" in text
    assert "minimalen read-only Evaluationsport" in text
    assert "persistente Operationbindung" in text


def test_roadmap_records_lq527_and_lq528() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-527 owner-controlled supervisor cleanup retention-eligibility operator contract:" in roadmap
    assert "lq-527-owner-controlled-supervisor-cleanup-retention-eligibility-operator-contract.md" in roadmap
    assert "nächster Slice LQ-528" in roadmap
