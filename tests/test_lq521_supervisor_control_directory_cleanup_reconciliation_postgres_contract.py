from pathlib import Path


ROOT = Path(__file__).parents[1]
TEST = ROOT / "tests/test_lq521_supervisor_control_directory_cleanup_reconciliation_postgres.py"


def _text() -> str:
    return TEST.read_text(encoding="utf-8")


def test_three_real_postgresql_crash_cases_are_parameterized() -> None:
    text = _text()
    assert "pytest.mark.postgres_integration" in text
    assert 'pytest.mark.parametrize("case", ("absent", "present", "conflict"))' in text
    assert "postgres_engine: Engine" in text
    assert "postgres_url: str" in text
    for forbidden in ("sqlite", "monkeypatch", "MagicMock", "Mock("):
        assert forbidden not in text


def test_full_claimed_attempt_clearance_and_write_claim_are_seeded() -> None:
    text = _text()
    assert "manifest_handoff_supervisor_control_cleanup_attempts" in text
    assert "'write_claimed'" in text
    assert "manifest_handoff_supervisor_cleanup_clearances" in text
    assert "manifest_handoff_supervisor_control_cleanup_write_claims" in text
    assert "write_claimed_at" in text


def test_physical_cases_are_distinct_and_snapshotted() -> None:
    text = _text()
    assert 'if case == "absent":' in text
    assert "leaf.rmdir()" in text
    assert 'elif case == "conflict":' in text
    assert 'unexpected.write_bytes(b"lq521-conflict")' in text
    assert "before = _physical_snapshot(root)" in text
    assert "_physical_snapshot(root) == before" in text


def test_real_reconcile_operator_and_closed_outcome_are_used() -> None:
    text = _text()
    assert 'root, "reconcile"' in text
    assert "operator.main(arguments)" in text
    assert '"outcome": case' in text
    assert "cleanup_control_directory" not in text


def test_unknown_security_and_terminal_reconciliation_are_persisted() -> None:
    text = _text()
    assert 'persisted.state == "reconciled"' in text
    assert "persisted.unknown_at is not None" in text
    assert "persisted.outcome is None" in text
    assert "persisted.completed_at is None" in text
    assert "persisted.reconciliation_outcome == case" in text
    assert "persisted.reconciled_at >= persisted.unknown_at >= persisted.write_claimed_at" in text
    assert "claims == 1" in text


def test_roadmap_records_lq521_and_lq522() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-521 PostgreSQL supervisor control-directory cleanup crash reconciliation proof:" in roadmap
    assert "lq-521-postgresql-supervisor-control-directory-cleanup-crash-reconciliation-proof.md" in roadmap
    assert "nächster Slice LQ-522" in roadmap
