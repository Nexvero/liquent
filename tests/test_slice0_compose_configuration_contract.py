from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "operations" / "compose" / "compose.yaml"
RUNTIME_EXAMPLE = ROOT / "operations" / "compose" / "runtime.env.example"
IMAGES_EXAMPLE = ROOT / "operations" / "compose" / "images.env.example"
DOC = ROOT / "docs" / "lq-057-slice-0-compose-configuration-contract.md"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _service_block(compose: str, service: str, next_service: str | None) -> str:
    marker = f"\n  {service}:\n"
    start = compose.index(marker) + 1
    end = (
        compose.index(f"\n  {next_service}:\n", start) + 1
        if next_service
        else compose.index("\nnetworks:\n")
    )
    return compose[start:end]


def test_contract_files_exist_and_are_documented() -> None:
    assert COMPOSE.is_file()
    assert RUNTIME_EXAMPLE.is_file()
    assert IMAGES_EXAMPLE.is_file()
    assert DOC.is_file()
    assert "lq-057-slice-0-compose-configuration-contract.md" in _text(ROOT / "README.md")


def test_compose_declares_required_roles_without_published_ports() -> None:
    compose = _text(COMPOSE)
    roles = ("migration-gate", "control-plane", "research-worker", "postgres", "prometheus", "grafana", "backup")
    for index, role in enumerate(roles):
        next_role = roles[index + 1] if index + 1 < len(roles) else None
        block = _service_block(compose, role, next_role)
        assert "\n    ports:" not in block
    assert "expose:" in _service_block(compose, "control-plane", "research-worker")


def test_compose_uses_existing_isolated_networks() -> None:
    compose = _text(COMPOSE)
    for network in ("liquent_public", "liquent_application", "liquent_data", "liquent_observability"):
        assert f"name: {network}" in compose
    postgres = _service_block(compose, "postgres", "prometheus")
    assert "- public" not in postgres
    worker = _service_block(compose, "research-worker", "postgres")
    assert "- public" not in worker


def test_images_require_operator_values_and_immutable_digest_examples() -> None:
    compose = _text(COMPOSE)
    examples = _text(IMAGES_EXAMPLE)
    for variable in (
        "LIQUENT_APP_IMAGE",
        "LIQUENT_POSTGRES_IMAGE",
        "LIQUENT_PROMETHEUS_IMAGE",
        "LIQUENT_GRAFANA_IMAGE",
    ):
        assert f"${{{variable}:?" in compose
        line = next(line for line in examples.splitlines() if line.startswith(f"{variable}="))
        assert "@sha256:" in line


def test_secrets_are_file_mounted_and_examples_contain_no_values() -> None:
    compose = _text(COMPOSE)
    assert "POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password" in compose
    assert "GF_SECURITY_ADMIN_PASSWORD__FILE: /run/secrets/grafana_admin_password" in compose
    assert "database_url:" in compose
    assert "password=" not in _text(RUNTIME_EXAMPLE).lower()
    assert "database_url=" not in _text(RUNTIME_EXAMPLE).lower()


def test_runtime_contract_disables_trading_and_limits_worker_concurrency() -> None:
    runtime = _text(RUNTIME_EXAMPLE)
    assert "LIQUENT_JOB_CONCURRENCY=1" in runtime
    assert "LIQUENT_TRADING_CONNECTIVITY=disabled" in runtime
    forbidden = ("BROKER", "EXCHANGE", "API_KEY", "API_SECRET", "LIVE_TRADING")
    assert not any(term in runtime for term in forbidden)


def test_services_have_resource_and_log_or_storage_controls() -> None:
    compose = _text(COMPOSE)
    app_base = compose[compose.index("x-app-base:"):compose.index("\nservices:\n")]
    assert "no-new-privileges:true" in app_base
    for role, next_role in (
        ("migration-gate", "control-plane"),
        ("control-plane", "research-worker"),
        ("research-worker", "postgres"),
        ("postgres", "prometheus"),
        ("prometheus", "grafana"),
        ("grafana", "backup"),
        ("backup", None),
    ):
        block = _service_block(compose, role, next_role)
        assert "cpus:" in block
        assert "mem_limit:" in block
        if role not in {"migration-gate", "control-plane", "research-worker"}:
            assert "no-new-privileges:true" in block
    assert "max-size: 10m" in compose
    assert "max-file: \"5\"" in compose
