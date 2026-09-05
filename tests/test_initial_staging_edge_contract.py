from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "operations" / "deploy"
PREFLIGHT = DEPLOY / "preflight-initial-staging.sh"
BOOTSTRAP = DEPLOY / "bootstrap-initial-staging.sh"
EDGE = ROOT / "operations" / "edge" / "staging.conf"
EDGE_COMPOSE = ROOT / "operations" / "edge" / "compose.edge.yaml"
EDGE_ENV_EXAMPLE = ROOT / "operations" / "edge" / "edge.env.example"
EDGE_CERT_INSTALL = ROOT / "operations" / "edge" / "install-staging-certificate.sh"
DIGEST = "sha256:" + "c" * 64
IMAGE = f"ghcr.io/nexvero/liquent@{DIGEST}"


def _fixture(tmp_path: Path) -> tuple[dict[str, str], Path, Path, Path]:
    compose = tmp_path / "compose.yaml"
    compose.write_text("name: test\nservices: {}\n", encoding="utf-8")
    runtime = tmp_path / "runtime.env"
    runtime.write_text("LIQUENT_ENVIRONMENT=production\n", encoding="utf-8")
    runtime.chmod(0o600)
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    for secret_name in ("database_url", "postgres_password"):
        secret = secrets / secret_name
        secret.write_text("fixture-value\n", encoding="utf-8")
        secret.chmod(0o600)
    images = tmp_path / "images.env"
    images.write_text(
        "\n".join(
            (
                f"LIQUENT_APP_IMAGE={IMAGE}",
                "LIQUENT_POSTGRES_IMAGE=postgres@sha256:" + "1" * 64,
                "LIQUENT_PROMETHEUS_IMAGE=prom/prometheus@sha256:" + "2" * 64,
                "LIQUENT_GRAFANA_IMAGE=grafana/grafana@sha256:" + "3" * 64,
                f"LIQUENT_SECRETS_DIR={secrets}",
                "",
            )
        ),
        encoding="utf-8",
    )
    deploy_config = tmp_path / "deploy.env"
    deploy_config.write_text(
        "\n".join(
            (
                f"COMPOSE_FILE={compose}",
                f"COMPOSE_ENV_FILE={images}",
                f"DEPLOY_STATE_DIR={tmp_path / 'state'}",
                "STAGING_HEALTH_URL=https://staging.liquent.ai/health/live",
                "",
            )
        ),
        encoding="utf-8",
    )
    deploy_config.chmod(0o600)

    cert = tmp_path / "fullchain.pem"
    key = tmp_path / "privkey.pem"
    subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(key), "-out", str(cert), "-days", "1",
            "-subj", "/CN=staging.liquent.ai",
            "-addext", "subjectAltName=DNS:staging.liquent.ai",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    key.chmod(0o600)
    edge_compose = tmp_path / "compose.edge.yaml"
    edge_compose.write_text("name: edge\nservices: {}\n", encoding="utf-8")
    edge_env = tmp_path / "edge.env"
    edge_env.write_text("LIQUENT_EDGE_IMAGE=nginx@sha256:" + "d" * 64 + "\n", encoding="utf-8")
    initial = tmp_path / "initial.env"
    initial.write_text(
        "\n".join(
            (
                "STAGING_HOST=staging.liquent.ai",
                "EXPECTED_IPV4=192.0.2.10",
                f"EDGE_COMPOSE_FILE={edge_compose}",
                f"EDGE_ENV_FILE={edge_env}",
                f"EDGE_CONFIG_FILE={tmp_path / 'edge.conf'}",
                f"EDGE_CERT_FILE={cert}",
                f"EDGE_KEY_FILE={key}",
                "",
            )
        ),
        encoding="utf-8",
    )
    initial.chmod(0o600)
    manifest = tmp_path / "release.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": "liquent.release-evidence.v1",
                "image": "ghcr.io/nexvero/liquent",
                "image_digest": DIGEST,
            }
        ),
        encoding="utf-8",
    )
    backup = tmp_path / "backup.evidence"
    backup.write_text("snapshot_id=abc\nverified_at=2026-07-26T12:00:00Z\n", encoding="utf-8")
    return {**os.environ, "LIQUENT_DEPLOY_CONFIG": str(deploy_config)}, initial, manifest, backup


def test_offline_initial_preflight_validates_tls_and_performs_no_mutation(tmp_path: Path) -> None:
    env, initial, manifest, backup = _fixture(tmp_path)
    result = subprocess.run(
        ["bash", str(PREFLIGHT), "--offline", IMAGE, str(manifest), str(backup), str(initial)],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    assert "no mutation performed" in result.stdout
    assert not (tmp_path / "state").exists()


def test_edge_exposes_only_liveness_and_denies_default_routes() -> None:
    config = EDGE.read_text(encoding="utf-8")
    assert "server_name staging.liquent.ai" in config
    assert "location = /health/live" in config
    assert "location ^~ /.well-known/acme-challenge/" in config
    assert "try_files $uri =404" in config
    assert "proxy_pass http://liquent_staging_control_plane/health/live" in config
    assert "location /" in config and "return 404" in config
    assert "/health/ready" not in config
    assert "/internal/metrics" not in config
    assert "ssl_protocols TLSv1.2 TLSv1.3" in config


def test_edge_compose_is_digest_bound_and_only_edge_publishes_ports() -> None:
    compose = EDGE_COMPOSE.read_text(encoding="utf-8")
    env_example = EDGE_ENV_EXAMPLE.read_text(encoding="utf-8")
    assert "image: ${LIQUENT_EDGE_IMAGE:?set an immutable nginx image digest}" in compose
    assert (
        "LIQUENT_EDGE_IMAGE=nginx@sha256:"
        "d5792f71a9496b833bc08ea834a758c46e2b6a6306c10f4be926f38a656cdc1c"
    ) in env_example
    assert '"80:80"' in compose and '"443:443"' in compose
    assert "read_only: true" in compose
    assert "no-new-privileges:true" in compose
    assert "cap_drop:\n      - ALL" in compose
    assert "./conf.d:/etc/nginx/conf.d:ro" in compose
    assert "./certs:/etc/nginx/certs:ro" in compose
    assert "/var/www/html:/var/www/html:ro" in compose
    assert "name: liquent_public" in compose


def test_edge_compose_has_bounded_health_and_logs() -> None:
    compose = EDGE_COMPOSE.read_text(encoding="utf-8")
    assert '"curl", "--fail", "--silent", "--show-error"' in compose
    assert "http://127.0.0.1/healthz" in compose
    assert "timeout: 3s" in compose
    assert "retries: 6" in compose
    assert "max-size: 10m" in compose
    assert 'max-file: "5"' in compose


def test_initial_bootstrap_requires_confirmation_and_orders_gates() -> None:
    script = BOOTSTRAP.read_text(encoding="utf-8")
    assert "INITIALIZE-STAGING" in script
    assert script.index("deploy_load_config") < script.index("preflight-initial-staging.sh")
    assert script.index("preflight-initial-staging.sh") < script.index('docker pull "$image"')
    assert script.index("deploy_ensure_network liquent_public false") < script.index("migration-gate")
    for name in ("liquent_application", "liquent_data", "liquent_observability"):
        assert f"deploy_ensure_network {name} true" in script
    assert script.index("migration-gate") < script.index("nginx -t")
    assert script.index("nginx -t") < script.index("deploy_external_health")
    assert "restore_initial_state" in script
    assert "deploy_compose stop control-plane" in script
    assert "deploy_compose stop postgres" in script
    assert "systemctl disable --now nginx" in script
    assert "systemctl enable nginx" in script
    assert "systemctl start nginx" in script


def test_initial_network_contract_validates_driver_and_isolation() -> None:
    library = (DEPLOY / "lib.sh").read_text(encoding="utf-8")
    preflight = PREFLIGHT.read_text(encoding="utf-8")
    assert "deploy_validate_network" in library
    assert '[[ "$driver" == "bridge" ]]' in library
    assert '[[ "$internal" == "$expected_internal" ]]' in library
    assert "docker network create --driver bridge --internal" in library
    assert "liquent_public:false" in preflight
    for name in ("liquent_application:true", "liquent_data:true", "liquent_observability:true"):
        assert name in preflight


def test_initial_preflight_binds_application_secret_to_runtime_identity() -> None:
    library = (DEPLOY / "lib.sh").read_text(encoding="utf-8")
    preflight = PREFLIGHT.read_text(encoding="utf-8")
    assert "deploy_require_file_owner" in library
    assert 'deploy_require_file_owner "$LIQUENT_SECRETS_DIR/database_url" 10001' in preflight
    assert '"$LIQUENT_SECRETS_DIR/postgres_password"' in preflight


def test_initial_bootstrap_never_publishes_extra_host_ports_or_credentials() -> None:
    combined = EDGE.read_text(encoding="utf-8") + BOOTSTRAP.read_text(encoding="utf-8")
    assert "docker login" not in combined
    assert "password" not in combined.lower()
    assert "ports:" not in EDGE.read_text(encoding="utf-8")


def test_initial_staging_scripts_have_valid_bash_syntax() -> None:
    for script in (PREFLIGHT, BOOTSTRAP, EDGE_CERT_INSTALL):
        subprocess.run(["bash", "-n", str(script)], check=True)


def test_initial_preflight_rejects_mutable_edge_image(tmp_path: Path) -> None:
    env, initial, manifest, backup = _fixture(tmp_path)
    edge_env = tmp_path / "edge.env"
    edge_env.write_text("LIQUENT_EDGE_IMAGE=nginx:latest\n", encoding="utf-8")
    result = subprocess.run(
        ["bash", str(PREFLIGHT), "--offline", IMAGE, str(manifest), str(backup), str(initial)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode != 0
    assert "immutable official nginx digest" in result.stderr


def test_initial_preflight_rejects_unpinned_infrastructure_image(tmp_path: Path) -> None:
    env, initial, manifest, backup = _fixture(tmp_path)
    images = tmp_path / "images.env"
    images.write_text(images.read_text().replace("postgres@sha256:" + "1" * 64, "postgres:18"))
    result = subprocess.run(
        ["bash", str(PREFLIGHT), "--offline", IMAGE, str(manifest), str(backup), str(initial)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode != 0
    assert "infrastructure image must use an immutable digest" in result.stderr


def test_initial_preflight_rejects_empty_runtime_configuration(tmp_path: Path) -> None:
    env, initial, manifest, backup = _fixture(tmp_path)
    (tmp_path / "runtime.env").write_text("", encoding="utf-8")
    result = subprocess.run(
        ["bash", str(PREFLIGHT), "--offline", IMAGE, str(manifest), str(backup), str(initial)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode != 0
    assert "required private file is empty" in result.stderr


def test_initial_preflight_rejects_missing_required_secret(tmp_path: Path) -> None:
    env, initial, manifest, backup = _fixture(tmp_path)
    (tmp_path / "secrets" / "database_url").unlink()
    result = subprocess.run(
        ["bash", str(PREFLIGHT), "--offline", IMAGE, str(manifest), str(backup), str(initial)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode != 0
    assert "required regular file missing" in result.stderr


def test_online_initial_preflight_requires_root_owned_sensitive_files() -> None:
    script = PREFLIGHT.read_text(encoding="utf-8")
    assert "deploy_require_root_owned_file" in script
    assert script.index("if (( ! offline ))") < script.index("deploy_require_root_owned_file")
    for name in ("runtime_env", "EDGE_KEY_FILE", "database_url", "postgres_password"):
        assert name in script


def test_certificate_install_hook_validates_before_atomic_replacement() -> None:
    script = EDGE_CERT_INSTALL.read_text(encoding="utf-8")
    assert "openssl x509" in script and "-checkhost" in script
    assert "certificate key mismatch" in script
    assert script.index("-checkhost") < script.index('install -d')
    assert "mktemp" in script
    assert 'mv -f "$fullchain_tmp"' in script
    assert 'mv -f "$private_key_tmp"' in script
    assert "ps --status running --services" in script
    assert "exec -T edge nginx -s reload" in script
