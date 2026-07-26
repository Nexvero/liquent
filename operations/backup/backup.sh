#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=operations/backup/lib.sh
source "$SCRIPT_DIR/lib.sh"

backup_load_config

if [[ "${1:-}" == "--check" ]]; then
    printf '[backup:ok] configuration valid; no repository or database access performed\n'
    exit 0
fi
[[ $# -eq 0 ]] || backup_die "usage: backup.sh [--check]"

for command in pg_dump restic sha256sum; do
    command -v "$command" >/dev/null || backup_die "required command not found: ${command}"
done
[[ -d "$ARTIFACT_ROOT" ]] || backup_die "artifact root not found: ${ARTIFACT_ROOT}"
mkdir -p "$BACKUP_DATABASE_DIR"
[[ -z "$(find "$BACKUP_DATABASE_DIR" -mindepth 1 -maxdepth 1 -print -quit)" ]] || \
    backup_die "database staging directory must be empty"

umask 077
dump_file="$BACKUP_DATABASE_DIR/liquent.dump"
manifest_file="$BACKUP_DATABASE_DIR/manifest.txt"
cleanup() {
    rm -f -- "$dump_file" "$manifest_file"
}
trap cleanup EXIT INT TERM

backup_export_credentials
pg_dump \
    --host "$POSTGRES_HOST" \
    --port "$POSTGRES_PORT" \
    --username "$POSTGRES_USER" \
    --dbname "$POSTGRES_DB" \
    --format custom \
    --file "$dump_file"

dump_sha256="$(sha256sum "$dump_file" | awk '{print $1}')"
{
    printf 'format=liquent-backup-v1\n'
    printf 'database_dump=liquent.dump\n'
    printf 'database_sha256=%s\n' "$dump_sha256"
    printf 'migration_head=%s\n' "${LIQUENT_MIGRATION_HEAD:-unknown}"
} > "$manifest_file"

restic --repo "$RESTIC_REPOSITORY" backup \
    --host "$BACKUP_HOST_ID" \
    --tag liquent-production \
    --tag schema-"${LIQUENT_MIGRATION_HEAD:-unknown}" \
    "$BACKUP_DATABASE_DIR" "$ARTIFACT_ROOT"
restic --repo "$RESTIC_REPOSITORY" check
printf '[backup:ok] encrypted snapshot created and repository metadata checked\n'
