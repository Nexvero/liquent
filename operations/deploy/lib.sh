#!/usr/bin/env bash
set -Eeuo pipefail

deploy_die() { printf '[deploy:error] %s\n' "$*" >&2; exit 1; }
deploy_info() { printf '[deploy] %s\n' "$*"; }

deploy_require_root() {
  [[ "$(id -u)" == 0 ]] || deploy_die "must run as root"
}

deploy_require_private_file() {
  local path="$1" mode
  [[ -f "$path" && ! -L "$path" ]] || deploy_die "required regular file missing: $path"
  if mode="$(stat -c '%a' "$path" 2>/dev/null)"; then :
  elif mode="$(stat -f '%Lp' "$path" 2>/dev/null)"; then :
  else deploy_die "cannot inspect permissions: $path"
  fi
  (( (8#$mode & 8#077) == 0 )) || deploy_die "permissions are too broad: $path"
}

deploy_require_nonempty_private_file() {
  deploy_require_private_file "$1"
  [[ -s "$1" ]] || deploy_die "required private file is empty: $1"
}

deploy_require_root_owned_file() {
  deploy_require_file_owner "$1" 0
}

deploy_require_file_owner() {
  local path="$1" expected_owner="$2" owner
  if owner="$(stat -c '%u' "$path" 2>/dev/null)"; then :
  elif owner="$(stat -f '%u' "$path" 2>/dev/null)"; then :
  else deploy_die "cannot inspect owner: $path"
  fi
  [[ "$owner" == "$expected_owner" ]] || deploy_die "file has unexpected owner: $path"
}

deploy_require_regular_file() {
  [[ -f "$1" && ! -L "$1" ]] || deploy_die "required regular file missing: $1"
}

deploy_is_digest_ref() {
  [[ "$1" =~ ^ghcr\.io/nexvero/liquent@sha256:[0-9a-f]{64}$ ]]
}

deploy_is_registry_digest_ref() {
  [[ "$1" =~ ^[A-Za-z0-9._/-]+@sha256:[0-9a-f]{64}$ ]]
}

deploy_load_config() {
  local config="${LIQUENT_DEPLOY_CONFIG:-/etc/liquent/deploy.env}"
  deploy_require_private_file "$config"
  # shellcheck disable=SC1090 -- root-owned, permission-checked operator config
  source "$config"
  for name in COMPOSE_FILE COMPOSE_ENV_FILE DEPLOY_STATE_DIR STAGING_HEALTH_URL; do
    [[ -n "${!name:-}" ]] || deploy_die "missing configuration: $name"
  done
  [[ "$COMPOSE_FILE" == /* && "$COMPOSE_ENV_FILE" == /* && "$DEPLOY_STATE_DIR" == /* ]] || \
    deploy_die "deployment paths must be absolute"
  [[ "$DEPLOY_STATE_DIR" != / ]] || deploy_die "state directory cannot be root"
  [[ "$STAGING_HEALTH_URL" =~ ^https://[^/]+/health/live$ ]] || \
    deploy_die "STAGING_HEALTH_URL must be HTTPS and end in /health/live"
  [[ -f "$COMPOSE_FILE" && -f "$COMPOSE_ENV_FILE" ]] || deploy_die "compose contract missing"
}

deploy_manifest_value() {
  jq -er "$2" "$1" 2>/dev/null || deploy_die "invalid release manifest field: $2"
}

deploy_validate_evidence() {
  local image="$1" manifest="$2" backup="$3" manifest_image manifest_digest
  deploy_is_digest_ref "$image" || deploy_die "image must be ghcr.io/nexvero/liquent@sha256:<64 hex>"
  deploy_require_regular_file "$manifest"
  deploy_require_regular_file "$backup"
  manifest_image="$(deploy_manifest_value "$manifest" '.image')"
  manifest_digest="$(deploy_manifest_value "$manifest" '.image_digest')"
  [[ "${manifest_image}@${manifest_digest}" == "$image" ]] || deploy_die "manifest does not match image digest"
  [[ "$(deploy_manifest_value "$manifest" '.schema')" == "liquent.release-evidence.v1" ]] || \
    deploy_die "unsupported release manifest schema"
  grep -Eq '^snapshot_id=[A-Za-z0-9:._/-]+$' "$backup" || deploy_die "backup evidence lacks snapshot_id"
  grep -Eq '^verified_at=[0-9]{4}-[0-9]{2}-[0-9]{2}T' "$backup" || deploy_die "backup evidence lacks verified_at"
}

deploy_current_image() {
  sed -n 's/^LIQUENT_APP_IMAGE=//p' "$COMPOSE_ENV_FILE" | tail -n 1
}

deploy_set_image() {
  local image="$1" temporary
  temporary="$(mktemp "${COMPOSE_ENV_FILE}.tmp.XXXXXX")"
  awk -v image="$image" '
    BEGIN { found=0 }
    /^LIQUENT_APP_IMAGE=/ { if (!found++) print "LIQUENT_APP_IMAGE=" image; next }
    { print }
    END { if (!found) print "LIQUENT_APP_IMAGE=" image }
  ' "$COMPOSE_ENV_FILE" > "$temporary"
  chmod --reference="$COMPOSE_ENV_FILE" "$temporary"
  chown --reference="$COMPOSE_ENV_FILE" "$temporary"
  mv -f "$temporary" "$COMPOSE_ENV_FILE"
}

deploy_compose() {
  docker compose --env-file "$COMPOSE_ENV_FILE" --file "$COMPOSE_FILE" "$@"
}

deploy_validate_network() {
  local name="$1" expected_internal="$2" driver internal
  if ! docker network inspect "$name" >/dev/null 2>&1; then
    return 1
  fi
  driver="$(docker network inspect --format '{{.Driver}}' "$name")"
  internal="$(docker network inspect --format '{{.Internal}}' "$name")"
  [[ "$driver" == "bridge" ]] || deploy_die "network must use bridge driver: $name"
  [[ "$internal" == "$expected_internal" ]] || deploy_die "network isolation mismatch: $name"
}

deploy_ensure_network() {
  local name="$1" expected_internal="$2"
  if deploy_validate_network "$name" "$expected_internal"; then
    return 0
  fi
  if [[ "$expected_internal" == true ]]; then
    docker network create --driver bridge --internal "$name" >/dev/null
  else
    docker network create --driver bridge "$name" >/dev/null
  fi
  deploy_validate_network "$name" "$expected_internal" || deploy_die "network creation failed validation: $name"
}

deploy_external_health() {
  local attempt payload
  for attempt in $(seq 1 30); do
    payload="$(curl --fail --silent --show-error --max-time 5 "$STAGING_HEALTH_URL" 2>/dev/null || true)"
    if jq -e '. == {status:"ok",service:"liquent-control-plane"}' <<<"$payload" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}
