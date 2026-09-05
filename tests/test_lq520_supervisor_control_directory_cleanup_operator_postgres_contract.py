from pathlib import Path


ROOT = Path(__file__).parents[1]
TEST = ROOT / "tests/test_lq520_supervisor_control_directory_cleanup_operator_postgres.py"


def _text() -> str:
    return TEST.read_text(encoding="utf-8")


def test_real_postgresql_fixture_and_real_operator_main_are_used() -> None:
    text = _text()
    assert "pytest.mark.postgres_integration" in text
    assert "postgres_engine: Engine" in text
    assert "postgres_url: str" in text
    assert "operator.main(execute)" in text
    assert "operator.main(reconcile)" in text
    for forbidden in ("sqlite", "monkeypatch", "MagicMock", "Mock("):
        assert forbidden not in text


def test_full_current_cleanup_authority_chain_is_seeded() -> None:
    text = _text()
    for table in (
        "identity_users", "manifest_handoff_registry_scopes",
        "manifest_handoff_supervisor_journal_jobs",
        "manifest_handoff_supervisor_journal_transitions",
        "manifest_handoff_supervisor_terminal_observations",
        "manifest_handoff_supervisor_control_directories",
        "manifest_handoff_supervisor_control_cleanup_decisions",
        "manifest_handoff_supervisor_cleanup_management_revisions",
        "manifest_handoff_supervisor_cleanup_{kind}_revisions",
    ):
        assert table in text
    assert 'for kind in ("hold", "recovery", "reference")' in text


def test_private_empty_leaf_is_removed_and_persistence_is_terminal() -> None:
    text = _text()
    assert "leaf_path.mkdir(mode=0o700)" in text
    assert 'executed["outcome"] == "removed"' in text
    assert "list(root.iterdir()) == []" in text
    assert 'attempt.state == "completed"' in text
    assert 'attempt.outcome == "removed"' in text
    assert "claims == 1" in text


def test_explicit_reconcile_of_completed_attempt_is_closed_and_effect_free() -> None:
    text = _text()
    execute = text.index("operator.main(execute)")
    reconcile = text.index("operator.main(reconcile)")
    assert execute < reconcile
    assert '"outcome": "rejected"' in text
    assert 'unchanged == ("completed", "removed", None)' in text
    assert "claim_count == 1" in text


def test_roadmap_records_lq520_and_lq521() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-520 PostgreSQL single supervisor control-directory cleanup operator proof:" in roadmap
    assert "lq-520-postgresql-single-supervisor-control-directory-cleanup-operator-proof.md" in roadmap
    assert "nächster Slice LQ-521" in roadmap
