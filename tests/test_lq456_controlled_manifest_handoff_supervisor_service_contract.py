from pathlib import Path


ROOT = Path(__file__).parents[1]
CONTRACT = ROOT / "docs/lq-456-controlled-manifest-handoff-supervisor-service-and-gate-contract.md"


def test_service_owns_processes_and_is_not_generic_runner() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "Supervisorservice besitzt alle Writer- und Recoverykindprozesse" in text
    assert "Anwendungscontroller sind ausschließlich authentisierte Clients" in text
    assert "kein Executable, Command, Args, Env, cwd oder Shell" in text


def test_prepare_journals_before_spawn_and_wrapper_gates_capability() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "Launch-Commit persistent appendieren" in text
    assert "Keine Prozessanlage findet vor Launch-Commit statt" in text
    assert "Wrapper lädt oder importiert noch keinen Writer- oder Reconcilerpfad" in text
    assert "Gatehandshake erfolgt vor jeder Capabilitywirkung" in text


def test_release_is_committed_and_consumed_once() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "LQ-455-Release-Commit mit stabiler Release-ID appendieren" in text
    assert "höchstens eine Release-ID konsumieren" in text
    assert "Gatewirkung vor durablem Release-Commit ist verboten" in text
    assert "erzeugt weder neue Release-ID noch neuen Gatekanal" in text


def test_terminal_requires_direct_end_and_termination_is_not_terminal() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "direktem Prozessende" in text
    assert "direkt beobachteter Endzeit" in text
    assert "Signalannahme, Timeout und Wrapper-EOF sind nicht terminal" in text
    assert "beobachtet weiter bis zum direkten Ende" in text


def test_restart_never_respawns_or_adopts() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "Er startet keinen davon erneut" in text
    assert "Launch-Commit darf niemals blind erneut gespawnt" in text
    assert "PID-Abwesenheit, Lockverlust" in text
    assert "adoptiert keinen ähnlich aussehenden Prozess" in text


def test_ipc_resources_and_detail_boundaries_are_closed() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "feste Versions- und\nGrößenlimits" in text
    assert "SessionPrincipal oder Rollen werden nicht" in text
    assert "detailfreie\ntechnische Unverfügbarkeit" in text


def test_slice_selects_no_primitive_schema_or_wiring() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "entscheidet noch keine konkrete Gate-, Spawn-, Reaper-" in text
    assert "keine Typen, Ports, Tabellen, Migrationen oder Adapter" in text
    assert "Head bleibt `20260824_0031`" in text
    assert "kein CLI-, Compose-, CI-, Deployment- oder Production-Wiring" in text


def test_roadmap_records_lq456_and_next_primitive_decision() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-456 controlled manifest handoff supervisor service and gate contract:" in roadmap
    assert "lq-456-controlled-manifest-handoff-supervisor-service-and-gate-contract.md" in roadmap
    assert "nächster Slice LQ-457" in roadmap
