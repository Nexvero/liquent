from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-471-persistent-manifest-handoff-supervisor-service-orchestration-contract.md"


def test_prepare_orders_launch_create_binding_start_ready_and_gated() -> None:
    text = DOC.read_text(encoding="utf-8")
    order = ["Launch-Commit dauerhaft appendieren", "Container über dieselbe Creation-ID",
             "Runtimebinding dauerhaft speichern", "gebundenen Container einmal starten",
             "dauerhaftes Ready", "Ready-Artefaktfakten dauerhaft korrelieren",
             "`prepared_gated` im Journal appendieren"]
    positions = [text.index(value, text.index("## 7. Prepare-Reihenfolge")) for value in order]
    assert positions == sorted(positions)


def test_release_orders_commit_token_ack_engine_and_running() -> None:
    text = DOC.read_text(encoding="utf-8")
    section = text[text.index("## 15. Release-Reihenfolge"):text.index("## 16. Commit vor Token")]
    order = ["Release-Commit", "Release-Token", "Token-Artefaktfakten", "Consumed-Ack",
             "Consumed-Fakten", "Engine-Running", "`running`"]
    positions = [section.index(value) for value in order]
    assert positions == sorted(positions)


def test_terminal_requires_outcome_envelope_engine_end_before_journal() -> None:
    text = DOC.read_text(encoding="utf-8")
    section = text[text.index("## 22. Terminale Reihenfolge"):text.index("## 23. Ende ohne Envelope")]
    order = ["Executed-Outcome", "Terminal-Envelope", "Envelope-Fakten",
             "exited/dead", "Envelope erneut", "Terminaltransition"]
    positions = [section.index(value) for value in order]
    assert positions == sorted(positions)
    assert "Exitcode allein ist kein fachlicher Outcome" in text


def test_termination_persists_before_engine_effect_and_waits_for_end() -> None:
    text = DOC.read_text(encoding="utf-8")
    section = text[text.index("## 26. Terminate-Reihenfolge"):text.index("## 27. Kein Signal vor Journal")]
    assert section.index("`termination_requested`") < section.index("Stop/Kill")
    assert section.index("Stop/Kill") < section.index("exited/dead")
    assert "Annahme nicht als Ende interpretieren" in section


def test_all_nonterminal_restart_states_are_fail_closed() -> None:
    text = DOC.read_text(encoding="utf-8")
    for state in ("PREPARE_REGISTERED", "LAUNCH_COMMITTED", "PREPARED_GATED",
                  "RELEASE_COMMITTED", "RUNNING", "TERMINATION_REQUESTED",
                  "TERMINAL_OBSERVED"):
        assert f"Restart {state}" in text
    assert "ruft weder Release noch Start erneut auf" in text
    assert "Abwesenheit ist kein Endnachweis" in text


def test_inspect_is_read_only_and_cross_system_absence_is_not_neutral() -> None:
    text = DOC.read_text(encoding="utf-8")
    section = text[text.index("## 28. Read-only Inspect"):text.index("## 29. Restart")]
    for forbidden in ("publiziert kein Token", "startet, released, terminiert und terminalisiert nichts"):
        assert forbidden in section
    assert "Unklare Wirkung wird nie als Nichtwirkung normalisiert" in text


def test_contract_adds_no_service_port_schema_or_wiring() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "ergänzt keinen Serviceport, Composer, Worker, Thread oder Entry Point" in text
    assert "Head bleibt `20260824_0032`" in text
    assert "keinen Seed, Backfill, CLI-, Route-, Compose- oder Production-Wiring" in text


def test_roadmap_records_lq471_and_next_service_values() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-471 persistent manifest handoff supervisor service orchestration contract:" in roadmap
    assert "lq-471-persistent-manifest-handoff-supervisor-service-orchestration-contract.md" in roadmap
    assert "nächster Slice LQ-472" in roadmap
