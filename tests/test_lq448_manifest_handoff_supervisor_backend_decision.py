from pathlib import Path


ROOT = Path(__file__).parents[1]
DECISION = (
    ROOT
    / "docs/lq-448-manifest-handoff-supervisor-backend-and-handle-persistence-decision.md"
)


def test_dedicated_controller_independent_supervisor_is_selected() -> None:
    text = DECISION.read_text(encoding="utf-8")
    assert "dedizierter controllerunabhängiger\nSupervisorservice mit eigenem durablem Journal" in text
    assert "Anwendungscomposition ist Client dieser Grenze" in text
    assert "kein allgemeiner Remote-Commandrunner" in text
    assert "Clientverlust ändert weder Jobidentität noch Gate-" in text


def test_registry_and_supervisor_sources_stay_separate() -> None:
    text = DECISION.read_text(encoding="utf-8")
    assert "Manifest-Handoff-Registry bindet fachlichen Claim" in text
    assert "Supervisorjournal bindet den opaken Jobhandle" in text
    assert "Supervisor entscheidet nicht, ob ein fachlicher Claim autorisiert ist" in text
    assert "Registry entscheidet nicht, ob ein konkreter Prozess noch wirkt" in text


def test_all_retry_and_observation_identities_are_stable() -> None:
    text = DECISION.read_text(encoding="utf-8")
    for value in (
        "Backendinstanz-ID",
        "Opaker Jobhandle",
        "Prepare-ID",
        "Release-ID",
        "Terminate-ID",
        "Terminale Observation",
    ):
        assert value in text
    assert "Ein zweites Prepare mit neuer ID ist verboten" in text
    assert "keine zweite physische Freigabe" in text


def test_process_end_and_unknown_resolution_remain_fail_closed() -> None:
    text = DECISION.read_text(encoding="utf-8")
    assert "PID, Container-ID oder Service-Manager-ID" in text
    assert "Exitcode, EOF oder verschwundener Prozess" in text
    assert "keine gemeinsame ACID-Transaktion" in text
    assert "stabile IDs und read-only Reconciliation" in text
    assert "unauflösbarer Handle ist dagegen\nnicht neutral" in text


def test_no_product_schema_port_process_or_wiring_is_selected() -> None:
    text = DECISION.read_text(encoding="utf-8")
    assert "nicht an\nDocker, systemd, launchd, Kubernetes" in text
    assert "keine\nTabelle, Spalte, SQL-Anweisung, Migration" in text
    assert "ändert keine LQ-446-Portsignatur" in text
    assert "Revision und Head bleiben `20260824_0029`" in text
    assert "kein CLI-, Compose-, CI-, Deployment- oder Production-Wiring" in text


def test_roadmap_records_lq448_and_platform_foundation_next() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-448 manifest handoff supervisor backend and handle persistence decision:" in roadmap
    assert "lq-448-manifest-handoff-supervisor-backend-and-handle-persistence-decision.md" in roadmap
    assert "nächster Slice LQ-449" in roadmap
