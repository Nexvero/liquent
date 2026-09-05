#!/usr/bin/env bash
set -Eeuo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/lib.sh"

[[ "$#" == 5 ]] || deploy_die "usage: bootstrap-initial-staging.sh IMAGE RELEASE-MANIFEST BACKUP-EVIDENCE INITIAL-CONFIG INITIALIZE-STAGING"
image="$1"; release_manifest="$2"; backup_evidence="$3"; initial_config="$4"; confirmation="$5"
[[ "$confirmation" == "INITIALIZE-STAGING" ]] || deploy_die "explicit INITIALIZE-STAGING confirmation required"
deploy_require_root
deploy_load_config
"$script_dir/preflight-initial-staging.sh" "$image" "$release_manifest" "$backup_evidence" "$initial_config"
# shellcheck disable=SC1090 -- validated by preflight
source "$initial_config"
for command in docker flock sha256sum install systemctl; do command -v "$command" >/dev/null || deploy_die "missing command: $command"; done

mkdir -p "$DEPLOY_STATE_DIR/runs"
chmod 0700 "$DEPLOY_STATE_DIR" "$DEPLOY_STATE_DIR/runs"
exec 9>"$DEPLOY_STATE_DIR/deploy.lock"
flock -n 9 || deploy_die "another deployment is active"
run_id="initial-$(date -u +%Y%m%dT%H%M%SZ)-$$"
run_dir="$DEPLOY_STATE_DIR/runs/$run_id"
mkdir -m 0700 "$run_dir"
cp -a "$COMPOSE_ENV_FILE" "$run_dir/images.env.before"
edge_config_existed=0
if [[ -f "$EDGE_CONFIG_FILE" ]]; then
  cp -a "$EDGE_CONFIG_FILE" "$run_dir/edge.conf.before"
  edge_config_existed=1
fi
printf '%s\n' "$image" > "$run_dir/candidate-image"
sha256sum "$release_manifest" "$backup_evidence" "$EDGE_CERT_FILE" > "$run_dir/evidence.sha256"
printf 'preparing\n' > "$run_dir/status"
host_nginx_active=0
host_nginx_enabled=0
systemctl is-active --quiet nginx && host_nginx_active=1
systemctl is-enabled --quiet nginx && host_nginx_enabled=1

restore_initial_state() {
  local status=$?
  trap - ERR
  printf 'failed\n' > "$run_dir/status"
  deploy_compose stop control-plane >/dev/null 2>&1 || true
  deploy_compose stop postgres >/dev/null 2>&1 || true
  cp -a "$run_dir/images.env.before" "$COMPOSE_ENV_FILE"
  docker compose --env-file "$EDGE_ENV_FILE" --file "$EDGE_COMPOSE_FILE" stop edge >/dev/null 2>&1 || true
  if (( edge_config_existed )); then
    cp -a "$run_dir/edge.conf.before" "$EDGE_CONFIG_FILE"
    docker compose --env-file "$EDGE_ENV_FILE" --file "$EDGE_COMPOSE_FILE" up --detach edge || true
  else
    rm -f -- "$EDGE_CONFIG_FILE"
  fi
  if (( host_nginx_enabled )); then systemctl enable nginx >/dev/null 2>&1 || true; fi
  if (( host_nginx_active )); then systemctl start nginx >/dev/null 2>&1 || true; fi
  exit "$status"
}
trap restore_initial_state ERR INT TERM

docker pull "$image"
deploy_set_image "$image"
deploy_ensure_network liquent_public false
deploy_ensure_network liquent_application true
deploy_ensure_network liquent_data true
deploy_ensure_network liquent_observability true
deploy_compose config --quiet
deploy_compose up --detach --wait postgres
deploy_compose run --rm migration-gate
deploy_compose up --detach --wait --no-deps control-plane
install -o root -g root -m 0644 "$script_dir/../edge/staging.conf" "$EDGE_CONFIG_FILE"
docker compose --env-file "$EDGE_ENV_FILE" --file "$EDGE_COMPOSE_FILE" run --rm edge nginx -t
systemctl disable --now nginx
docker compose --env-file "$EDGE_ENV_FILE" --file "$EDGE_COMPOSE_FILE" up --detach --wait edge
deploy_external_health
printf 'complete\n' > "$run_dir/status"
trap - ERR INT TERM
deploy_info "initial staging bootstrap complete: run_id=$run_id image=$image"
