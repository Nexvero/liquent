import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
COMPOSE = ROOT / "operations/compose/compose.yaml"
RUNTIME = ROOT / "operations/compose/runtime.env.example"
CONFIG = ROOT / "operations/compose/research-worker.json.example"
README = ROOT / "operations/compose/README.md"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _worker(compose: str) -> str:
    start = compose.index("\n  research-worker:\n")
    return compose[start:compose.index("\n  postgres:\n", start)]


def test_worker_receives_only_explicit_entry_point_files() -> None:
    worker = _worker(_text(COMPOSE))
    assert "- liquent-research-worker" in worker
    assert "- --configuration\n      - /run/liquent/research-worker.json" in worker
    assert "- --database-url-file\n      - /run/secrets/database_url" in worker
    assert 'uid: "10001"' in worker
    assert 'gid: "10001"' in worker
    assert "mode: 0400" in worker
    assert "LIQUENT_RESEARCH_WORKER_CONFIG_FILE" in worker
    assert "LIQUENT_RESEARCH_WORKER_ID_FILE" in worker
    assert "database_url" not in _text(RUNTIME).lower()


def test_inputs_are_read_only_and_only_artifacts_are_worker_writable() -> None:
    worker = _worker(_text(COMPOSE))
    assert "/run/liquent/research-worker.json:ro" in worker
    assert "/run/liquent/research-worker-id:ro" in worker
    assert "/var/lib/liquent/research-data:ro" in worker
    assert "artifacts:/var/lib/liquent/artifacts" in worker
    assert "artifacts:/var/lib/liquent/artifacts:ro" not in worker
    assert "- public" not in worker


def test_example_is_closed_and_matches_container_mount_targets() -> None:
    values = json.loads(_text(CONFIG))
    assert set(values) == {
        "worker_id_path", "research_data_root", "artifact_root",
        "lease_seconds", "idle_wait_seconds",
        "unavailable_initial_wait_seconds", "unavailable_max_wait_seconds",
        "jitter_max_seconds", "job_concurrency", "trading_connectivity",
    }
    assert values["worker_id_path"] == "/run/liquent/research-worker-id"
    assert values["research_data_root"] == "/var/lib/liquent/research-data"
    assert values["artifact_root"] == "/var/lib/liquent/artifacts"
    assert values["job_concurrency"] == 1
    assert values["trading_connectivity"] == "disabled"


def test_runtime_order_and_operator_responsibility_are_explicit() -> None:
    compose = _text(COMPOSE)
    worker = _worker(compose)
    assert "migration-gate:\n        condition: service_completed_successfully" in worker
    assert "stop_grace_period: 60s" in worker
    readme = _text(README)
    assert "does not create identities, datasets, secrets, or config" in readme
    assert "runtime UID must own" in readme
