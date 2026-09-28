import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
DOMAIN = ROOT / "src/liquent_platform/identity/manifest_handoff_supervisor_journal.py"
PORTS = ROOT / "src/liquent_platform/identity/ports.py"


def _classes(path: Path) -> dict[str, ast.ClassDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}


def _methods(node: ast.ClassDef) -> list[str]:
    return [item.name for item in node.body if isinstance(item, ast.FunctionDef)]


def test_three_repr_free_journal_ids_and_seven_states() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    assert text.count("value: str = field(repr=False)") == 3
    for state in (
        "prepare_registered", "launch_committed", "prepared_gated",
        "release_committed", "running", "termination_requested", "terminal_observed",
    ):
        assert f'= "{state}"' in text


def test_writer_and_recovery_registration_and_terminal_types_are_separate() -> None:
    classes = _classes(DOMAIN)
    assert {
        "RegisterManifestHandoffWriterJournalJob",
        "RegisterManifestHandoffRecoveryJournalJob",
        "RecordManifestHandoffWriterJournalTerminal",
        "RecordManifestHandoffRecoveryJournalTerminal",
        "ManifestHandoffWriterJournalView",
        "ManifestHandoffRecoveryJournalView",
    } <= classes.keys()
    assert "ManifestHandoffWriterSupervisorRequest" in ast.unparse(classes["RegisterManifestHandoffWriterJournalJob"])
    assert "ManifestHandoffRecoverySupervisorRequest" in ast.unparse(classes["RegisterManifestHandoffRecoveryJournalJob"])


def test_transition_requests_have_no_free_payload_or_process_controls() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    for forbidden in ("command:", "args:", "env:", "cwd:", "timeout:", "signal:", "payload:", "SessionPrincipal"):
        assert forbidden not in text
    assert "result.handle_id != handle" in text


def test_writer_and_recovery_ports_have_eight_closed_methods_each() -> None:
    classes = _classes(PORTS)
    writer = _methods(classes["ManifestHandoffWriterSupervisorJournal"])
    recovery = _methods(classes["ManifestHandoffRecoverySupervisorJournal"])
    assert len(writer) == 8 and len(recovery) == 8
    assert writer == [
        "register_writer", "commit_writer_launch", "record_writer_gated",
        "commit_writer_release", "record_writer_running",
        "request_writer_termination", "record_writer_terminal",
        "inspect_writer_journal",
    ]
    assert recovery[-1] == "inspect_recovery_journal"


def test_ports_expose_no_generic_mutation_or_authority_parameters() -> None:
    classes = _classes(PORTS)
    forbidden = {"principal", "allow", "role", "command", "clock", "now"}
    for name in (
        "ManifestHandoffWriterSupervisorJournal",
        "ManifestHandoffRecoverySupervisorJournal",
    ):
        assert not {"set_state", "append"} & set(_methods(classes[name]))
        for item in classes[name].body:
            if isinstance(item, ast.FunctionDef):
                assert not forbidden & {arg.arg for arg in item.args.args}


def test_slice_has_no_persistence_process_or_transport_import() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    for forbidden in ("sqlalchemy", "alembic", "subprocess", "socket", "docker"):
        assert forbidden not in text
    assert "ManifestHandoffSupervisorJournalConflict" in text


def test_roadmap_records_lq453_and_next_foundation() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-453 manifest handoff supervisor journal types and ports:" in roadmap
    assert "lq-453-manifest-handoff-supervisor-journal-types-and-ports.md" in roadmap
    assert "nächster Slice LQ-454" in roadmap
