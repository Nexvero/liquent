#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=operations/backup/lib.sh
source "$SCRIPT_DIR/lib.sh"

backup_load_config
[[ "${1:-}" == "--apply" && $# -eq 1 ]] || \
    backup_die "retention requires explicit --apply"
backup_export_credentials
command -v restic >/dev/null || backup_die "required command not found: restic"

restic --repo "$RESTIC_REPOSITORY" forget \
    --host "$BACKUP_HOST_ID" \
    --tag liquent-production \
    --group-by host,tags \
    --keep-daily 7 \
    --keep-weekly 4 \
    --keep-monthly 6 \
    --prune
restic --repo "$RESTIC_REPOSITORY" check
printf '[backup:ok] retention applied and repository metadata checked\n'
