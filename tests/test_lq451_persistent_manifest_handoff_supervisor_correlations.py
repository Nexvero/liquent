import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "src/liquent_platform/persistence/manifest_handoff_supervisor_correlations.py"


def _class() -> ast.ClassDef:
    tree = ast.parse(ADAPTER.read_text(encoding="utf-8"))
    return next(node for node in tree.body if isinstance(node, ast.ClassDef))


def test_adapter_implements_backend_store_and_lookup_surface() -> None:
    methods = {
        node.name for node in _class().body if isinstance(node, ast.FunctionDef)
    }
    assert {
        "resolve", "reserve_writer", "reserve_recovery", "bind_handle",
        "record_release", "record_termination", "record_terminal_observation",
        "resolve_preparation", "resolve_handle", "resolve_release",
        "resolve_termination", "resolve_terminal_observation",
    } <= methods


def test_current_backend_is_uncached_and_exactly_one_active() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    assert "WHERE status='active'" in text
    assert "if not rows:\n                return None" in text
    assert "if len(rows) != 1:" in text
    assert "_backend_cache" not in text


def test_preparations_validate_backend_claim_owner_and_terminal_state() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    assert 'backend[0].status != "active"' in text
    assert "claim.owner_id != values[\"owner\"] or claim.end_id is not None" in text
    assert 'capability == "recovery" and claim.ended_at is not None' in text
    assert "_PREPARE_BY_EXECUTION" in text and "_PREPARE_BY_RECOVERY" in text


def test_writer_release_requires_claimed_start_and_active_backend() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    assert "_WRITER_START" in text
    assert "require_releasable=True" in text
    assert "handle.capability == \"writer\"" in text
    assert "handle.capability == \"recovery\"" in text


def test_operation_ids_are_idempotent_and_handle_unique() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    assert "_RELEASE_BY_HANDLE" in text
    assert "_TERMINATION_BY_HANDLE" in text
    assert "_TERMINAL_BY_HANDLE" in text
    assert "row.handle_id != values[\"handle\"]" in text
    assert "ManifestHandoffSupervisorCorrelationConflict()" in text


def test_reads_are_exact_and_all_failures_are_detail_free() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    assert "def _read(self, action):" in text
    assert "def _write(self, action):" in text
    assert text.count("raise ManifestHandoffRegistryUnavailable") >= 10
    assert "str(error)" not in text and "raise error" not in text


def test_adapter_has_no_process_authority_or_wiring_capability() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    for forbidden in (
        "subprocess", "SessionPrincipal", "shell=True", "docker", "Popen",
        "actor_user_id", "allow=", "role=",
    ):
        assert forbidden not in text


def test_roadmap_records_lq451_and_next_journal_contract() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-451 persistent manifest handoff supervisor correlations:" in roadmap
    assert "lq-451-persistent-manifest-handoff-supervisor-correlations.md" in roadmap
    assert "nächster Slice LQ-452" in roadmap
