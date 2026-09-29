from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-2762-staging-reconciliation-exercise-decision-packet.md"
RUNBOOK = ROOT / "operations/runbooks/staging-promotion.md"


def test_packet_is_one_bounded_decision_not_executable_authority() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "one future staging reconciliation exercise" in text
    assert "evidence of a decision only" in text
    assert "not a credential, reusable\nauthorization token" in text
    assert "applies only to the named exercise\nwindow" in text


def test_packet_has_fixed_minimal_fields_and_decisions() -> None:
    text = DOC.read_text(encoding="utf-8")
    for field in (
        "environment_boundary_confirmed: yes|no",
        "settings_custody_confirmed: yes|no",
        "provider_read_authorized: yes|no",
        "postgresql_readiness_confirmed: yes|no",
        "durable_candidate_confirmed: yes|no",
        "operator_role_assigned: yes|no",
        "approver_role_assigned: yes|no",
        "incident_response_role_assigned: yes|no",
        "window_start_utc: YYYY-MM-DDTHH:MM:SSZ",
        "window_expires_utc: YYYY-MM-DDTHH:MM:SSZ",
        "decision: approved|rejected|expired",
        "decision_recorded_utc: YYYY-MM-DDTHH:MM:SSZ",
    ):
        assert field in text


def test_packet_is_fail_closed_and_single_use() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "every confirmation is exactly `yes`" in text
    assert "decision other than `approved` stops the exercise" in text
    assert "no implied approval\nand no fail-open default" in text
    assert "cannot authorize a\nretry, second candidate, polling, bulk drain" in text
    assert "A new pass requires a new packet" in text


def test_packet_excludes_private_and_personal_material() -> None:
    text = DOC.read_text(encoding="utf-8")
    for phrase in (
        "a settings path or value",
        "provider endpoint, response, receipt or error detail",
        "database URL, host, schema revision or credential",
        "operation identity or durable-record payload",
        "personal name, account, email address or contact detail",
        "command output, stack trace, token or secret",
    ):
        assert phrase in text


def test_runbook_links_the_packet_without_turning_it_into_a_credential() -> None:
    runbook = RUNBOOK.read_text(encoding="utf-8")
    assert "lq-2762-staging-reconciliation-exercise-decision-packet.md" in runbook
    assert "Only an unexpired `approved` packet" in runbook
    assert "every confirmation set to `yes`" in runbook
    assert "It is not a\ncredential and cannot be reused" in runbook
