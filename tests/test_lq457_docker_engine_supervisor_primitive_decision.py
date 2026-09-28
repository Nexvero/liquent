from pathlib import Path


ROOT = Path(__file__).parents[1]
DECISION = ROOT / "docs/lq-457-docker-engine-supervisor-process-and-gate-primitive-decision.md"


def test_linux_local_docker_engine_is_selected_without_fallback() -> None:
    text = DECISION.read_text(encoding="utf-8")
    assert "kontrollierte Linux-Hosts" in text
    assert "lokalem Docker Engine Daemon" in text
    assert "Remote Daemons" in text
    assert "keinen Popen-, systemd- oder Threadfallback" in text


def test_container_identity_restart_and_removal_are_fail_closed() -> None:
    text = DECISION.read_text(encoding="utf-8")
    assert "Restartpolicy ist zwingend `no`" in text
    assert "nicht mit Auto-Remove beziehungsweise `--rm`" in text
    assert "Container-ID an Backendinstanz, Journalhandle und Launch-Commit" in text
    assert "ruft nicht blind `start` erneut auf" in text


def test_image_mount_network_and_privilege_profiles_are_closed() -> None:
    text = DECISION.read_text(encoding="utf-8")
    assert "per\nDigest gebundenen Image" in text
    assert "Source ausschließlich read-only" in text
    assert "Recovery erhält Target ausschließlich read-only" in text
    assert "standardmäßig kein Netzwerk" in text
    assert "Privileged, Host-PID, Host-Network" in text


def test_gate_uses_durable_token_and_consumed_ack() -> None:
    text = DECISION.read_text(encoding="utf-8")
    assert "unveränderliches Release-Token" in text
    assert "unveränderliches Release-consumed-Ack" in text
    assert "atomare No-replace-Veröffentlichung" in text
    assert "Vor Capabilitycode veröffentlicht der Wrapper" in text
    assert "Token-/Ack-Übereinstimmung" in text


def test_terminal_requires_bound_runtime_and_closed_envelope() -> None:
    text = DECISION.read_text(encoding="utf-8")
    assert "Engine `exited` oder `dead`" in text
    assert "valides Resultatenvelope" in text
    assert "Exitcode allein erzeugt keinen fachlichen Erfolg" in text
    assert "persistierte Container-ID nicht auflösen" in text
    assert "Recovery bleibt gesperrt" in text


def test_slice_changes_no_schema_adapter_container_or_wiring() -> None:
    text = DECISION.read_text(encoding="utf-8")
    assert "keine Typen, Ports, Tabellen, Migrationen oder Adapter" in text
    assert "Head bleibt `20260824_0031`" in text
    assert "erstellt kein Image, Verzeichnis oder Container" in text
    assert "kein CLI-, Compose-, CI-, Deployment- oder Production-Wiring" in text


def test_roadmap_records_lq457_and_next_foundation() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-457 docker engine supervisor process and gate primitive decision:" in roadmap
    assert "lq-457-docker-engine-supervisor-process-and-gate-primitive-decision.md" in roadmap
    assert "nächster Slice LQ-458" in roadmap
