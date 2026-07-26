#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

check_only=0
[[ "${1:-}" == "--check" ]] && { check_only=1; shift; }
[[ "$#" == 3 ]] || deploy_die "usage: promote-staging.sh [--check] IMAGE@sha256:DIGEST RELEASE-MANIFEST BACKUP-EVIDENCE"
image="$1"; release_manifest="$2"; backup_evidence="$3"

deploy_load_config
deploy_validate_evidence "$image" "$release_manifest" "$backup_evidence"
previous_image="$(deploy_current_image)"
deploy_is_digest_ref "$previous_image" || deploy_die "a valid previous staging digest is required for automatic rollback"

if (( check_only )); then
  deploy_info "preflight valid; no mutation performed"
  exit 0
fi

deploy_require_root
for command in docker curl jq flock sha256sum; do command -v "$command" >/dev/null || deploy_die "missing command: $command"; done
mkdir -p "$DEPLOY_STATE_DIR/runs"
chmod 0700 "$DEPLOY_STATE_DIR" "$DEPLOY_STATE_DIR/runs"
exec 9>"$DEPLOY_STATE_DIR/deploy.lock"
flock -n 9 || deploy_die "another deployment is active"

run_id="$(date -u +%Y%m%dT%H%M%SZ)-$$"
run_dir="$DEPLOY_STATE_DIR/runs/$run_id"
mkdir -m 0700 "$run_dir"
cp -a "$COMPOSE_ENV_FILE" "$run_dir/images.env.before"
printf '%s\n' "$previous_image" > "$run_dir/previous-image"
printf '%s\n' "$image" > "$run_dir/candidate-image"
sha256sum "$release_manifest" "$backup_evidence" > "$run_dir/evidence.sha256"
printf 'preparing\n' > "$run_dir/status"

rollback_on_error() {
  local status=$?
  trap - ERR
  printf 'failed\n' > "$run_dir/status"
  deploy_info "promotion failed; restoring previous application digest"
  cp -a "$run_dir/images.env.before" "$COMPOSE_ENV_FILE"
  deploy_compose up --detach --no-deps control-plane || true
  exit "$status"
}
trap rollback_on_error ERR INT TERM

docker pull "$image"
deploy_set_image "$image"
deploy_compose config --quiet
deploy_compose up --detach --wait postgres
deploy_compose run --rm migration-gate
deploy_compose up --detach --wait --no-deps control-plane
deploy_external_health
printf 'complete\n' > "$run_dir/status"
trap - ERR INT TERM
deploy_info "promotion complete: run_id=$run_id image=$image"
