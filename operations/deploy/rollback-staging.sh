#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

[[ "$#" == 1 && "$1" =~ ^[0-9]{8}T[0-9]{6}Z-[0-9]+$ ]] || deploy_die "usage: rollback-staging.sh RUN_ID"
run_id="$1"
deploy_require_root
deploy_load_config
for command in docker curl jq flock; do command -v "$command" >/dev/null || deploy_die "missing command: $command"; done
run_dir="$DEPLOY_STATE_DIR/runs/$run_id"
[[ -d "$run_dir" && ! -L "$run_dir" ]] || deploy_die "unknown deployment run: $run_id"
previous_image="$(<"$run_dir/previous-image")"
deploy_is_digest_ref "$previous_image" || deploy_die "recorded previous image is invalid"

exec 9>"$DEPLOY_STATE_DIR/deploy.lock"
flock -n 9 || deploy_die "another deployment is active"
docker pull "$previous_image"
deploy_set_image "$previous_image"
deploy_compose config --quiet
deploy_compose up --detach --wait --no-deps control-plane
deploy_external_health
printf 'rolled_back\n' > "$run_dir/status"
deploy_info "application rollback complete; database migrations were not reversed"
