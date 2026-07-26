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
DIGEST = "sha256:" + "c" * 64
IMAGE = f"ghcr.io/nexvero/liquent@{DIGEST}"


def _fixture(tmp_path: Path) -> tuple[dict[str, str], Path, Path, Path]:
    compose = tmp_path / "compose.yaml"
    compose.write_text("name: test\nservices: {}\n", encoding="utf-8")
    images = tmp_path / "images.env"
    images.write_text("LIQUENT_APP_IMAGE=bootstrap-placeholder\n", encoding="utf-8")
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
    edge_env.write_text("NGINX_IMAGE=nginx@example\n", encoding="utf-8")
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
    assert "proxy_pass http://liquent_staging_control_plane/health/live" in config
    assert "location /" in config and "return 404" in config
    assert "/health/ready" not in config
    assert "/internal/metrics" not in config
    assert "ssl_protocols TLSv1.2 TLSv1.3" in config


def test_initial_bootstrap_requires_confirmation_and_orders_gates() -> None:
    script = BOOTSTRAP.read_text(encoding="utf-8")
    assert "INITIALIZE-STAGING" in script
    assert script.index("preflight-initial-staging.sh") < script.index('docker pull "$image"')
    assert script.index("migration-gate") < script.index("nginx -t")
    assert script.index("nginx -t") < script.index("deploy_external_health")
    assert "restore_initial_state" in script
    assert "deploy_compose stop control-plane" in script


def test_initial_bootstrap_never_publishes_extra_host_ports_or_credentials() -> None:
    combined = EDGE.read_text(encoding="utf-8") + BOOTSTRAP.read_text(encoding="utf-8")
    assert "docker login" not in combined
    assert "password" not in combined.lower()
    assert "ports:" not in EDGE.read_text(encoding="utf-8")


def test_initial_staging_scripts_have_valid_bash_syntax() -> None:
    for script in (PREFLIGHT, BOOTSTRAP):
        subprocess.run(["bash", "-n", str(script)], check=True)
