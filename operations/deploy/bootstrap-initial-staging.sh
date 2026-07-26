#!/usr/bin/env bash
set -Eeuo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/lib.sh"

[[ "$#" == 5 ]] || deploy_die "usage: bootstrap-initial-staging.sh IMAGE RELEASE-MANIFEST BACKUP-EVIDENCE INITIAL-CONFIG INITIALIZE-STAGING"
image="$1"; release_manifest="$2"; backup_evidence="$3"; initial_config="$4"; confirmation="$5"
[[ "$confirmation" == "INITIALIZE-STAGING" ]] || deploy_die "explicit INITIALIZE-STAGING confirmation required"
deploy_require_root
"$script_dir/preflight-initial-staging.sh" "$image" "$release_manifest" "$backup_evidence" "$initial_config"
# shellcheck disable=SC1090 -- validated by preflight
source "$initial_config"
for command in docker flock sha256sum install; do command -v "$command" >/dev/null || deploy_die "missing command: $command"; done

mkdir -p "$DEPLOY_STATE_DIR/runs"
chmod 0700 "$DEPLOY_STATE_DIR" "$DEPLOY_STATE_DIR/runs"
exec 9>"$DEPLOY_STATE_DIR/deploy.lock"
flock -n 9 || deploy_die "another deployment is active"
run_id="initial-$(date -u +%Y%m%dT%H%M%SZ)-$$"
run_dir="$DEPLOY_STATE_DIR/runs/$run_id"
mkdir -m 0700 "$run_dir"
cp -a "$COMPOSE_ENV_FILE" "$run_dir/images.env.before"
if [[ -f "$EDGE_CONFIG_FILE" ]]; then cp -a "$EDGE_CONFIG_FILE" "$run_dir/edge.conf.before"; fi
printf '%s\n' "$image" > "$run_dir/candidate-image"
sha256sum "$release_manifest" "$backup_evidence" "$EDGE_CERT_FILE" > "$run_dir/evidence.sha256"
printf 'preparing\n' > "$run_dir/status"

restore_initial_state() {
  local status=$?
  trap - ERR
  printf 'failed\n' > "$run_dir/status"
  deploy_compose stop control-plane >/dev/null 2>&1 || true
  cp -a "$run_dir/images.env.before" "$COMPOSE_ENV_FILE"
  if [[ -f "$run_dir/edge.conf.before" ]]; then
    cp -a "$run_dir/edge.conf.before" "$EDGE_CONFIG_FILE"
    docker compose --env-file "$EDGE_ENV_FILE" --file "$EDGE_COMPOSE_FILE" up --detach edge || true
  fi
  exit "$status"
}
trap restore_initial_state ERR INT TERM

docker pull "$image"
deploy_set_image "$image"
deploy_compose config --quiet
deploy_compose up --detach --wait postgres
deploy_compose run --rm migration-gate
deploy_compose up --detach --wait --no-deps control-plane
install -o root -g root -m 0644 "$script_dir/../edge/staging.conf" "$EDGE_CONFIG_FILE"
docker compose --env-file "$EDGE_ENV_FILE" --file "$EDGE_COMPOSE_FILE" run --rm edge nginx -t
docker compose --env-file "$EDGE_ENV_FILE" --file "$EDGE_COMPOSE_FILE" up --detach --wait edge
deploy_external_health
printf 'complete\n' > "$run_dir/status"
trap - ERR INT TERM
deploy_info "initial staging bootstrap complete: run_id=$run_id image=$image"
