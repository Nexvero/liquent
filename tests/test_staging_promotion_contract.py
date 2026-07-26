from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "operations" / "deploy"
PROMOTE = DEPLOY / "promote-staging.sh"
ROLLBACK = DEPLOY / "rollback-staging.sh"
LIB = DEPLOY / "lib.sh"
DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64


def _fixture(tmp_path: Path) -> tuple[dict[str, str], str, Path, Path]:
    compose = tmp_path / "compose.yaml"
    compose.write_text("name: liquent-test\nservices: {}\n", encoding="utf-8")
    images = tmp_path / "images.env"
    images.write_text(f"LIQUENT_APP_IMAGE=ghcr.io/nexvero/liquent@{DIGEST_A}\n", encoding="utf-8")
    state = tmp_path / "state"
    config = tmp_path / "deploy.env"
    config.write_text(
        "\n".join(
            (
                f"COMPOSE_FILE={compose}",
                f"COMPOSE_ENV_FILE={images}",
                f"DEPLOY_STATE_DIR={state}",
                "STAGING_HEALTH_URL=https://staging.example.test/health/live",
                "",
            )
        ),
        encoding="utf-8",
    )
    config.chmod(0o600)
    manifest = tmp_path / "release-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": "liquent.release-evidence.v1",
                "image": "ghcr.io/nexvero/liquent",
                "image_digest": DIGEST_B,
            }
        ),
        encoding="utf-8",
    )
    backup = tmp_path / "backup.evidence"
    backup.write_text(
        "snapshot_id=staging:abc123\nverified_at=2026-07-26T12:00:00Z\n",
        encoding="utf-8",
    )
    env = {**os.environ, "LIQUENT_DEPLOY_CONFIG": str(config)}
    return env, f"ghcr.io/nexvero/liquent@{DIGEST_B}", manifest, backup


def test_staging_preflight_accepts_bound_digest_without_mutation(tmp_path: Path) -> None:
    env, image, manifest, backup = _fixture(tmp_path)
    result = subprocess.run(
        ["bash", str(PROMOTE), "--check", image, str(manifest), str(backup)],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    assert "no mutation performed" in result.stdout
    assert not (tmp_path / "state").exists()


def test_staging_preflight_rejects_tag_instead_of_digest(tmp_path: Path) -> None:
    env, _, manifest, backup = _fixture(tmp_path)
    result = subprocess.run(
        ["bash", str(PROMOTE), "--check", "ghcr.io/nexvero/liquent:latest", str(manifest), str(backup)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode != 0
    assert "sha256" in result.stderr


def test_promotion_orders_backup_evidence_migration_health_and_journal() -> None:
    script = PROMOTE.read_text(encoding="utf-8")
    assert script.index("deploy_validate_evidence") < script.index('docker pull "$image"')
    assert script.index("migration-gate") < script.index("deploy_external_health")
    for status in ("preparing", "failed", "complete"):
        assert status in script
    assert "rollback_on_error" in script
    assert "images.env.before" in script


def test_rollback_is_application_only_and_uses_recorded_digest() -> None:
    script = ROLLBACK.read_text(encoding="utf-8")
    assert "previous-image" in script
    assert "deploy_is_digest_ref" in script
    assert "--no-deps control-plane" in script
    assert "database migrations were not reversed" in script
    assert "alembic downgrade" not in script


def test_deployment_scripts_have_valid_bash_syntax() -> None:
    for script in (LIB, PROMOTE, ROLLBACK):
        subprocess.run(["bash", "-n", str(script)], check=True)
