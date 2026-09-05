from pathlib import Path


ROOT = Path(__file__).parents[1]
DECISION = ROOT / "docs/lq-447-local-manifest-handoff-supervisor-feasibility-decision.md"


def test_decision_rejects_unsafe_local_process_implementations() -> None:
    text = DECISION.read_text(encoding="utf-8")
    assert "Ein einfacher lokaler Adapter wird nicht\nimplementiert" in text
    for value in (
        "`subprocess.Popen` allein nicht genügt",
        "PID plus Startzeit nicht genügt",
        "PID-Datei nicht genügt",
        "Lockfile nicht genügt",
        "Pipe-EOF nicht genügt",
        "Parent-Death-Signal nicht genügt",
        "Threadadapter unzulässig",
        "`multiprocessing` allein nicht genügt",
    ):
        assert value in text


def test_controller_independent_backend_and_durable_bindings_are_required() -> None:
    text = DECISION.read_text(encoding="utf-8")
    assert "Controllerunabhängige Beobachtung" in text
    assert "Claim, Owner, Capability und Backendhandle benötigen eine durable" in text
    assert "opake stabile Backend-Handle-ID" in text
    assert "Ein Claim darf höchstens einen vorbereiteten Supervisorprozess" in text
    assert "Fehlende Auflösung ist technische Unverfügbarkeit, nicht Prozessende" in text


def test_prepare_release_terminate_and_terminal_facts_need_stable_ids() -> None:
    text = DECISION.read_text(encoding="utf-8")
    assert "Gatefreigabe benötigt eine eigene stabile intern erzeugte Release-ID" in text
    assert "stabile terminale Observation-ID" in text
    assert "Terminierung benötigt ebenfalls eine stabile intern erzeugte Request-ID" in text
    assert "Prepare-Unknown" in text
    assert "Release-Unknown" in text
    assert "Check-then-call mit neuer ID nach Fehler ist verboten" in text


def test_no_fallback_authority_or_existing_attempt_fiction_is_opened() -> None:
    text = DECISION.read_text(encoding="utf-8")
    assert "nicht auf\nin-memory `Popen`, Thread, PID-Datei oder direkten Writeraufruf zurückfallen" in text
    assert "Supervisorquelle erteilt keine Execution- oder Recoveryauthority" in text
    assert "Bestehende Attempts besitzen keine Supervisorhandlehistorie" in text
    assert "erzeugen keinen Backfill" in text


def test_slice_changes_no_process_schema_or_ports() -> None:
    text = DECISION.read_text(encoding="utf-8")
    assert "keine Tabelle, Spalte, Migration, Domainklasse oder Portsignatur" in text
    assert "Revision und Head bleiben `20260824_0029`" in text
    assert "keinen neuen Subprocess-, Fork-, Thread-, Container-" in text
    assert "Kein CLI-, Compose-, CI- oder Production-Wiring" in text


def test_roadmap_records_decision_and_next_slice() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-447 local manifest handoff supervisor feasibility decision:" in roadmap
    assert "`docs/lq-447-local-manifest-handoff-supervisor-feasibility-decision.md`" in roadmap
    assert "nächster Slice LQ-448" in roadmap
