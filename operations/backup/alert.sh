#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=operations/backup/lib.sh
source "$SCRIPT_DIR/lib.sh"

config_file="${LIQUENT_BACKUP_ALERT_CONFIG:-/etc/liquent/backup-alert.env}"
backup_require_file "$config_file"
# shellcheck disable=SC1090
source "$config_file"
backup_require_var ALERT_RECIPIENT
backup_require_var ALERT_ACCOUNT
backup_require_var ALERT_HOST
[[ "$ALERT_RECIPIENT" =~ ^[^[:space:]@]+@[^[:space:]@]+$ ]] || \
    backup_die "invalid alert recipient"
[[ "$ALERT_ACCOUNT" =~ ^[A-Za-z0-9._-]+$ ]] || backup_die "invalid alert account"
[[ "$ALERT_HOST" =~ ^[A-Za-z0-9._-]+$ ]] || backup_die "invalid alert host"
command -v msmtp >/dev/null || backup_die "required command not found: msmtp"

reason="${1:-backup operation failed}"
[[ "$reason" != *$'\n'* && "$reason" != *$'\r'* ]] || backup_die "invalid alert reason"
{
    printf 'From: Liquent Backup <%s>\n' "$ALERT_RECIPIENT"
    printf 'To: %s\n' "$ALERT_RECIPIENT"
    printf 'Subject: [Liquent %s] Backup alert\n' "$ALERT_HOST"
    printf 'Date: %s\n' "$(LC_ALL=C date -R)"
    printf '\n%s\n' "$reason"
    printf 'Host: %s\n' "$ALERT_HOST"
    printf 'Time: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} | msmtp --account="$ALERT_ACCOUNT" "$ALERT_RECIPIENT"
