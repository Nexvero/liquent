from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_local_resolver_binds_result_to_snapshot_identity() -> None:
    source = (ROOT / "src/liquent_platform/application/local_csv.py").read_text()
    assert "class _SnapshotBoundBacktestExecution" in source
    assert "replace(self._runner.run(), experiment_id=self._experiment_id)" in source
    assert "str(snapshot.experiment_id)" in source


def test_persistent_success_uses_json_safe_evidence_projection() -> None:
    source = (ROOT / "src/liquent_platform/persistence/research_jobs.py").read_text()
    assert "json.dumps(evidence_document(summary)" in source
    assert "allow_nan=False" in source
    assert "summary.experiment_id != str(snapshot.experiment_id)" in source


def test_roadmap_records_green_postgresql_chain_and_next_audit() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    section = roadmap.split("- LQ-547 PostgreSQL research worker identity and evidence stabilization:", 1)[1]
    section = section.split("\n- LQ-192", 1)[0]
    assert "PostgreSQL-Suite mit 105 Tests" in section
    assert "normale Suite mit 5023" in section
    assert "nächster Slice LQ-548" in section
