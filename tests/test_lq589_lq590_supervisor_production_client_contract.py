from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_reaudit_closes_only_the_directory_blocker() -> None:
    document = _read("docs/lq-589-supervisor-production-wiring-blocker-reaudit.md")

    assert "Directory-Blocker" in document
    assert "Engineclient" in document
    assert "Capabilityprimitive" in document
    assert "Settings-only-Wiring" in document
    assert "SessionPrincipal" in document
    assert "Production-Wiring bleibt deshalb geschlossen" in document


def test_client_contract_is_local_closed_and_inert() -> None:
    document = _read("docs/lq-590-closed-local-docker-engine-http-client-contract.md")

    for required in (
        "absoluten Unix-Socketpfad",
        "DOCKER_HOST",
        "feste unterstützte Konstante",
        "Find, Create, Inspect, Start, Wait",
        "Stop und Kill",
        "Remove, Exec, Attach, Logs, Pull, Build",
        "close()` ist idempotent",
        "Konstruktor öffnet keinen Socket",
        "bestehende detailfreie technische Grenze",
        "keine Session",
    ):
        assert required in document


def test_followup_settings_do_not_prematurely_wire_runtime_files() -> None:
    settings = _read("src/liquent_platform/configuration.py")
    app = _read("src/liquent_platform/transport/http/app.py")
    compose = _read("operations/compose/compose.yaml")
    environment = _read("operations/compose/runtime.env.example")

    assert "manifest handoff supervisor settings must be provided together" in settings
    assert "compose_candidate_manifest_handoff_supervisor_graph" not in app
    assert "compose_persistent_manifest_handoff_supervisor_service" not in app
    assert "/var/run/docker.sock" not in compose
    assert "LIQUENT_MANIFEST_HANDOFF_SUPERVISOR_MODE=candidate" in environment
    assert "# LIQUENT_MANIFEST_HANDOFF_SUPERVISOR_MODE=candidate" in environment


def test_roadmap_records_the_two_slice_sequence() -> None:
    roadmap = _read("docs/technical-status-and-roadmap.md")

    assert "LQ-589 supervisor production wiring blocker re-audit" in roadmap
    assert "LQ-590 closed local Docker engine HTTP client contract" in roadmap
    assert "nächster Slice LQ-591 implementiert die Grenze" in roadmap
