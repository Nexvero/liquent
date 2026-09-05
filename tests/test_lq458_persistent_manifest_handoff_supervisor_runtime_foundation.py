from pathlib import Path


ROOT = Path(__file__).parents[1]
MIGRATION = ROOT / "src/liquent_platform/persistence/alembic/versions/20260824_0032_manifest_handoff_supervisor_runtime.py"


def test_revision_is_linear_empty_and_additive() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert 'revision: str = "20260824_0032"' in text
    assert 'down_revision: str | Sequence[str] | None = "20260824_0031"' in text
    assert "INSERT" not in text and "UPDATE" not in text and "op.bulk_insert" not in text


def test_runtime_binding_is_one_to_one_and_non_reassignable() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert '"handle_id", name="pk_manifest_handoff_supervisor_runtime_bindings"' in text
    assert "uq_manifest_handoff_supervisor_runtime_creation" in text
    assert "uq_manifest_handoff_supervisor_runtime_container" in text
    assert "uq_manifest_handoff_supervisor_runtime_control_directory" in text
    assert "manifest_handoff_supervisor_journal_jobs.handle_id" in text


def test_image_is_digest_pinned_and_no_host_path_is_stored() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert "length(image_digest)=71" in text
    assert "substr(image_digest,1,7)='sha256:'" in text
    assert "control_directory_path" not in text
    assert "engine_socket" not in text and "host_path" not in text


def test_control_artifacts_have_four_closed_once_only_roles() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    for role in ("wrapper_ready", "release_token", "release_consumed", "terminal_envelope"):
        assert f"'{role}'" in text
    assert "uq_manifest_handoff_supervisor_control_artifact_role" in text
    assert "length(artifact_sha256)=64 AND byte_count>0" in text


def test_foundation_has_two_tables_no_cascade_and_reverse_downgrade() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert text.count("op.create_table(") == 2
    assert "ondelete=" not in text
    drops = [line.strip() for line in text.splitlines() if "op.drop_table" in line]
    assert "control_artifacts" in drops[0] and "runtime_bindings" in drops[1]


def test_migration_gates_are_synchronized_to_32() -> None:
    gate = (ROOT / "tests/test_persistence_migration_gate.py").read_text()
    bundle = (ROOT / "tools/operational_release_bundle.py").read_text()
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    assert 'expected_head() == "20260826_0042"' in gate
    assert "EXPECTED_MIGRATION_COUNT = 42" in bundle
    assert "**42 lineare Migrationen**, Head\n  `20260826_0042`" in roadmap


def test_roadmap_records_lq458_and_next_types_slice() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    assert "- LQ-458 persistent manifest handoff supervisor runtime foundation:" in roadmap
    assert "lq-458-persistent-manifest-handoff-supervisor-runtime-foundation.md" in roadmap
    assert "nächster Slice LQ-459" in roadmap
