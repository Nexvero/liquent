from __future__ import annotations

import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
BACKUP_ROOT = ROOT / "operations" / "backup"
BACKUP_DOCKERFILE = ROOT / "Dockerfile.backup"
BACKUP_SMOKE = ROOT / "operations" / "container" / "backup-smoke-test.sh"
SCRIPTS = (
    BACKUP_ROOT / "lib.sh",
    BACKUP_ROOT / "backup.sh",
    BACKUP_ROOT / "retention.sh",
    BACKUP_ROOT / "restore-verify.sh",
)


def _checked_config(tmp_path: Path) -> Path:
    secrets = {}
    for name in ("restic_password", "ovh_access_key", "ovh_secret_key", "pgpass"):
        path = tmp_path / name
        path.write_text("placeholder\n", encoding="utf-8")
        path.chmod(0o600)
        secrets[name] = path
    database_dir = tmp_path / "database"
    artifacts = tmp_path / "artifacts"
    database_dir.mkdir()
    artifacts.mkdir()
    config = tmp_path / "backup.env"
    config.write_text(
        "\n".join(
            (
                "RESTIC_REPOSITORY=s3:https://s3.example.invalid/bucket/liquent",
                f"RESTIC_PASSWORD_FILE={secrets['restic_password']}",
                f"OVH_ACCESS_KEY_FILE={secrets['ovh_access_key']}",
                f"OVH_SECRET_KEY_FILE={secrets['ovh_secret_key']}",
                f"PGPASSFILE={secrets['pgpass']}",
                "POSTGRES_HOST=postgres",
                "POSTGRES_PORT=5432",
                "POSTGRES_DB=liquent",
                "POSTGRES_USER=liquent",
                f"BACKUP_DATABASE_DIR={database_dir}",
                f"ARTIFACT_ROOT={artifacts}",
                "BACKUP_HOST_ID=liquent-test",
                "LIQUENT_MIGRATION_HEAD=test-head",
                "",
            )
        ),
        encoding="utf-8",
    )
    config.chmod(0o600)
    return config


def test_backup_scripts_have_valid_bash_syntax() -> None:
    for script in (*SCRIPTS, BACKUP_SMOKE):
        subprocess.run(["bash", "-n", str(script)], check=True)


def test_backup_image_uses_pinned_tools_and_non_root_runtime() -> None:
    dockerfile = BACKUP_DOCKERFILE.read_text(encoding="utf-8")
    assert "postgres:18.6-trixie@sha256:" in dockerfile
    assert "restic/restic:0.18.1@sha256:" in dockerfile
    assert "COPY --from=restic /usr/bin/restic" in dockerfile
    assert "USER 10001:10001" in dockerfile
    assert "ENTRYPOINT []" in dockerfile
    assert '["/opt/liquent/backup/backup.sh", "--check"]' in dockerfile


def test_quality_workflow_builds_and_smokes_backup_image() -> None:
    workflow = (ROOT / ".github" / "workflows" / "quality.yml").read_text(
        encoding="utf-8"
    )
    assert "backup-container:" in workflow
    assert "--file Dockerfile.backup" in workflow
    assert "backup-smoke-test.sh" in workflow
    assert '10001:10001' in workflow


def test_backup_and_restore_check_mode_perform_no_external_commands(tmp_path: Path) -> None:
    config = _checked_config(tmp_path)
    env = {**os.environ, "LIQUENT_BACKUP_CONFIG": str(config), "PATH": "/usr/bin:/bin"}
    for script in (BACKUP_ROOT / "backup.sh", BACKUP_ROOT / "restore-verify.sh"):
        result = subprocess.run(
            ["bash", str(script), "--check"],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        assert "configuration valid" in result.stdout


def test_configuration_rejects_insecure_secret_permissions(tmp_path: Path) -> None:
    config = _checked_config(tmp_path)
    config.chmod(0o644)
    result = subprocess.run(
        ["bash", str(BACKUP_ROOT / "backup.sh"), "--check"],
        capture_output=True,
        text=True,
        env={**os.environ, "LIQUENT_BACKUP_CONFIG": str(config)},
    )
    assert result.returncode != 0
    assert "permissions are too broad" in result.stderr


def test_retention_requires_explicit_apply_and_matches_policy() -> None:
    script = (BACKUP_ROOT / "retention.sh").read_text(encoding="utf-8")
    assert '"--apply"' in script
    assert "--keep-daily 7" in script
    assert "--keep-weekly 4" in script
    assert "--keep-monthly 6" in script
    assert "--prune" in script


def test_restore_refuses_existing_target_and_validates_dump() -> None:
    script = (BACKUP_ROOT / "restore-verify.sh").read_text(encoding="utf-8")
    assert '[[ ! -e "$target" ]]' in script
    assert 'actual_sha256' in script
    assert 'pg_restore --list "$dump_file"' in script


def test_backup_contains_database_dump_artifacts_manifest_and_check() -> None:
    script = (BACKUP_ROOT / "backup.sh").read_text(encoding="utf-8")
    assert "pg_dump" in script
    assert '"$BACKUP_DATABASE_DIR" "$ARTIFACT_ROOT"' in script
    assert "database_sha256=" in script
    assert 'restic --repo "$RESTIC_REPOSITORY" check' in script


def test_runbook_requires_isolated_restore_and_records_rpo_rto() -> None:
    runbook = (ROOT / "operations" / "runbooks" / "backup-restore.md").read_text(
        encoding="utf-8"
    )
    for term in ("isolated", "RPO", "RTO", "snapshot ID", "never into Production"):
        assert term in runbook
