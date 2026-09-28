from pathlib import Path


ROOT = Path(__file__).parents[1]
CONTRACT = ROOT / "docs/lq-452-durable-manifest-handoff-supervisor-journal-contract.md"


def test_contract_has_linear_append_only_job_state() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    for state in (
        "prepare_registered", "launch_committed", "prepared_gated",
        "release_committed", "running", "termination_requested",
        "terminal_observed",
    ):
        assert state in text
    assert "Zustände werden nicht zurückgesetzt oder überschrieben" in text
    assert "frei mutierbares `current_state`" in text


def test_prepare_is_durable_and_never_spawns_twice() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "Vor jeder Prozessanlage journalisiert" in text
    assert "Vor der physischen Prozessanlage entsteht genau ein stabiler Launch-Commit" in text
    assert "unklarer Launch wird nicht durch einen zweiten Spawn" in text
    assert "Retry startet niemals einen zweiten Prozess" in text


def test_gate_release_is_once_and_unknown_is_read_only() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "Es gibt höchstens einen physischen Gateverbrauch" in text
    assert "konsumiert die stabile Release-ID höchstens einmal" in text
    assert "erzeugt keine neue Release-ID und keinen neuen Gatekanal" in text
    assert "Inspect startet, released, signalisiert und adoptiert nichts" in text


def test_termination_never_substitutes_for_terminal_observation() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "Terminierung ist nicht terminal" in text
    assert "Signalversand, Signalannahme, Timeout" in text
    assert "terminal_observed` wird genau einmal" in text
    assert "PID-Abwesenheit, EOF, Lockverlust" in text


def test_results_remain_closed_and_recovery_read_only() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "Writerterminalität verwendet exakt die fünf LQ-446-Arten" in text
    assert "Recoveryterminalität verwendet exakt fünf LQ-427-Arten plus unknown" in text
    assert "Commit- und Stagingfreigaben bleiben immer false" in text
    assert "Recovery führt keine Dateimutation aus" in text


def test_restart_does_not_adopt_or_infer_processes() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "wiederholt keinen Spawn und keine Gatewirkung aus Vermutung" in text
    assert "Keine Prozessadoption" in text
    assert "PID-, Name-, Commandline- oder Pfadähnlichkeit reicht nicht" in text
    assert "journalisierter, aber nicht auflösbarer Job ist nicht neutral" in text


def test_slice_changes_no_schema_ports_process_or_wiring() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "keine Tabelle, Datei, Embedded Database, Logengine" in text
    assert "keine Migration, Domainklasse oder Portsignatur" in text
    assert "Head bleibt `20260824_0030`" in text
    assert "kein CLI-, Compose-, CI-, Deployment- oder Production-Wiring" in text


def test_roadmap_records_lq452_and_next_types_slice() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-452 durable manifest handoff supervisor journal contract:" in roadmap
    assert "lq-452-durable-manifest-handoff-supervisor-journal-contract.md" in roadmap
    assert "nächster Slice LQ-453" in roadmap
