#!/usr/bin/env bash

set -euo pipefail

backup_die() {
    printf '[backup:error] %s\n' "$*" >&2
    exit 1
}

backup_require_var() {
    local name="$1"
    [[ -n "${!name:-}" ]] || backup_die "missing configuration: ${name}"
}

backup_require_file() {
    local path="$1"
    local mode
    [[ -f "$path" ]] || backup_die "required file not found: ${path}"
    [[ ! -L "$path" ]] || backup_die "secret file must not be a symlink: ${path}"
    if mode="$(stat -c '%a' "$path" 2>/dev/null)"; then
        :
    elif mode="$(stat -f '%Lp' "$path" 2>/dev/null)"; then
        :
    else
        backup_die "cannot inspect file permissions: ${path}"
    fi
    if (( (8#$mode & 8#077) != 0 )); then
        backup_die "secret file permissions are too broad: ${path}"
    fi
}

backup_require_safe_dir() {
    local path="$1"
    [[ "$path" == /* ]] || backup_die "path must be absolute: ${path}"
    [[ "$path" != "/" ]] || backup_die "root directory is never a valid target"
}

backup_load_config() {
    local config_file="${LIQUENT_BACKUP_CONFIG:-/etc/liquent/backup.env}"
    backup_require_file "$config_file"
    # shellcheck disable=SC1090 -- operator-selected, permission-checked file
    source "$config_file"
    for name in \
        RESTIC_REPOSITORY RESTIC_PASSWORD_FILE OVH_ACCESS_KEY_FILE \
        OVH_SECRET_KEY_FILE PGPASSFILE POSTGRES_HOST POSTGRES_PORT \
        POSTGRES_DB POSTGRES_USER BACKUP_DATABASE_DIR ARTIFACT_ROOT \
        BACKUP_HOST_ID; do
        backup_require_var "$name"
    done
    backup_require_file "$RESTIC_PASSWORD_FILE"
    backup_require_file "$OVH_ACCESS_KEY_FILE"
    backup_require_file "$OVH_SECRET_KEY_FILE"
    backup_require_file "$PGPASSFILE"
    backup_require_safe_dir "$BACKUP_DATABASE_DIR"
    backup_require_safe_dir "$ARTIFACT_ROOT"
    [[ "$RESTIC_REPOSITORY" == s3:https://* ]] || \
        backup_die "RESTIC_REPOSITORY must use s3:https"
}

backup_export_credentials() {
    export RESTIC_PASSWORD_FILE PGPASSFILE
    IFS= read -r AWS_ACCESS_KEY_ID < "$OVH_ACCESS_KEY_FILE"
    IFS= read -r AWS_SECRET_ACCESS_KEY < "$OVH_SECRET_KEY_FILE"
    [[ -n "$AWS_ACCESS_KEY_ID" && -n "$AWS_SECRET_ACCESS_KEY" ]] || \
        backup_die "object-storage credential file is empty"
    export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
}
