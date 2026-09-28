#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
stamp="${LIQUENT_BACKUP_SUCCESS_STAMP:-/var/lib/liquent-backup/last-success}"
maximum_age_seconds="${LIQUENT_BACKUP_MAXIMUM_AGE_SECONDS:-86400}"
[[ "$maximum_age_seconds" =~ ^[1-9][0-9]*$ ]] || {
    printf '[backup-age:error] invalid maximum age\n' >&2
    exit 1
}
if [[ ! -f "$stamp" || -L "$stamp" ]]; then
    "$SCRIPT_DIR/alert.sh" "No successful backup timestamp is recorded."
    exit 1
fi
age_seconds=$(( $(date -u +%s) - $(stat -c %Y "$stamp") ))
if (( age_seconds > maximum_age_seconds )); then
    "$SCRIPT_DIR/alert.sh" "The last successful backup is older than 24 hours."
    exit 1
fi
printf '[backup-age:ok] last successful backup is within 24 hours\n'
