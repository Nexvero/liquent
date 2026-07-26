#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=operations/backup/lib.sh
source "$SCRIPT_DIR/lib.sh"

backup_load_config

if [[ "${1:-}" == "--check" ]]; then
    printf '[restore:ok] configuration valid; no snapshot restored\n'
    exit 0
fi
[[ "${1:-}" == "--target" && -n "${2:-}" && $# -eq 2 ]] || \
    backup_die "usage: restore-verify.sh --target /isolated/empty/directory"
target="$2"
backup_require_safe_dir "$target"
[[ ! -e "$target" ]] || backup_die "restore target must not already exist"

for command in restic pg_restore sha256sum; do
    command -v "$command" >/dev/null || backup_die "required command not found: ${command}"
done
backup_export_credentials
umask 077
mkdir -p -- "$target"

restic --repo "$RESTIC_REPOSITORY" restore latest \
    --host "$BACKUP_HOST_ID" \
    --tag liquent-production \
    --target "$target"

restored_database_dir="$target$BACKUP_DATABASE_DIR"
dump_file="$restored_database_dir/liquent.dump"
manifest_file="$restored_database_dir/manifest.txt"
[[ -f "$dump_file" && -f "$manifest_file" ]] || \
    backup_die "snapshot does not contain the database dump and manifest"
expected_sha256="$(awk -F= '$1 == "database_sha256" {print $2}' "$manifest_file")"
[[ -n "$expected_sha256" ]] || backup_die "manifest has no database checksum"
actual_sha256="$(sha256sum "$dump_file" | awk '{print $1}')"
[[ "$actual_sha256" == "$expected_sha256" ]] || backup_die "database dump checksum mismatch"
pg_restore --list "$dump_file" >/dev/null

printf '[restore:ok] snapshot restored to isolated target; dump checksum and catalog valid\n'
printf '[restore:next] database import, application start and functional sampling remain manual gates\n'
