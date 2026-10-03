#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

die() { printf 'staging research proof: %s\n' "$1" >&2; exit 2; }
require_value() { [[ -n "${!1:-}" ]] || die "missing configuration: $1"; }

check_only=0
[[ "${1:-}" == "--check" ]] && { check_only=1; shift; }
[[ "$#" == 0 ]] || die "usage: staging-proof.sh [--check]"
config="${LIQUENT_RESEARCH_PROOF_CONFIG:-/etc/liquent/research-proof.env}"
[[ -f "$config" && ! -L "$config" ]] || die "configuration must be a regular file"
config_mode="$(stat -f '%Lp' "$config" 2>/dev/null || stat -c '%a' "$config")"
[[ "$config_mode" == 600 ]] || die "configuration must have mode 0600"
# shellcheck disable=SC1090
source "$config"
for name in CONTROL_PLANE_CONTAINER RESEARCH_WORKER_CONTAINER MEMBERSHIP_BASE_REQUEST EVIDENCE_ROOT STAGING_ORIGIN DATABASE_URL_SECRET ARTIFACT_ROOT; do
  require_value "$name"
done
[[ "$STAGING_ORIGIN" == https://* && "$STAGING_ORIGIN" != */ ]] || die "invalid staging origin"
[[ -f "$MEMBERSHIP_BASE_REQUEST" && ! -L "$MEMBERSHIP_BASE_REQUEST" ]] || die "membership request must be a regular file"
if (( check_only )); then
  printf '%s\n' 'configuration valid; no mutation performed'
  exit 0
fi
[[ "$EUID" == 0 ]] || die "root is required"
for command in curl docker jq sha256sum; do command -v "$command" >/dev/null || die "missing command: $command"; done

run_id="$(date -u +%Y%m%dT%H%M%SZ)-research-proof"
run_dir="$EVIDENCE_ROOT/$run_id"
install -d -m 0700 "$EVIDENCE_ROOT" "$run_dir"
container_dir="/tmp/$run_id"
grant_applied=0
revoke_done=0

put_in_container() {
  docker exec -i "$CONTROL_PLANE_CONTAINER" /bin/sh -c 'umask 077; cat > "$1"' sh "$2" < "$1"
}

apply_membership() {
  local request="$1" stem="$2"
  local container_request="$container_dir/${stem}-request.json"
  local container_result="$container_dir/${stem}-result.json"
  docker exec "$CONTROL_PLANE_CONTAINER" /bin/sh -c 'install -d -m 0700 "$1"' sh "$container_dir"
  put_in_container "$request" "$container_request"
  docker exec "$CONTROL_PLANE_CONTAINER" liquent-membership-management apply \
    --database-url-file "$DATABASE_URL_SECRET" --request "$container_request" \
    --result-file "$container_result" > "$run_dir/${stem}-outcome.json"
  docker exec "$CONTROL_PLANE_CONTAINER" cat "$container_result" > "$run_dir/${stem}-result.json"
  chmod 0600 "$run_dir/${stem}-result.json" "$run_dir/${stem}-outcome.json"
  docker exec "$CONTROL_PLANE_CONTAINER" rm -f "$container_request" "$container_result"
  [[ "$(jq -r '.outcome' "$run_dir/${stem}-outcome.json")" == applied ]]
}

revoke_write() {
  local change_id revision
  change_id="$(docker exec "$CONTROL_PLANE_CONTAINER" liquent-membership-management new-change-id)"
  revision="$(jq -er '.revision_id' "$run_dir/grant-result.json")"
  jq --arg change "$change_id" --arg revision "$revision" \
    '.change_id=$change | .expected_revision=$revision | .permissions=["research:read"]' \
    "$run_dir/grant-request.json" > "$run_dir/revoke-request.json"
  chmod 0600 "$run_dir/revoke-request.json"
  apply_membership "$run_dir/revoke-request.json" revoke
  revoke_done=1
}

cleanup() {
  local result="$1"
  trap - EXIT
  if (( grant_applied == 1 && revoke_done == 0 )) && ! revoke_write; then
    result=1
    printf '%s\n' 'write_permission_revocation=failed' >&2
  fi
  docker exec "$CONTROL_PLANE_CONTAINER" rm -r "$container_dir" >/dev/null 2>&1 || true
  rm -f "$run_dir/session-id" "$run_dir/csrf-token" "$run_dir/cookies.txt" "$run_dir/headers.txt"
  exit "$result"
}
trap 'cleanup $?' EXIT

docker exec "$CONTROL_PLANE_CONTAINER" /bin/sh -c 'install -d -m 0700 "$1"' sh "$container_dir"
put_in_container "$MEMBERSHIP_BASE_REQUEST" "$container_dir/base-request.json"
docker exec -i "$CONTROL_PLANE_CONTAINER" python - "$container_dir/base-request.json" "$container_dir/current.json" "$DATABASE_URL_SECRET" <<'PY'
import json, os, sys
from pathlib import Path
from sqlalchemy import create_engine, text
request = json.loads(Path(sys.argv[1]).read_text())
engine = create_engine(Path(sys.argv[3]).read_text().strip())
try:
    values = {"target": request["target_user_id"].encode(), "workspace": request["workspace_id"].encode()}
    with engine.connect() as connection:
        row = connection.execute(text("SELECT revision_id,status FROM workspace_memberships WHERE user_id=:target AND workspace_id=:workspace"), values).one()
        permissions = connection.execute(text("SELECT permission FROM workspace_membership_permissions WHERE user_id=:target AND workspace_id=:workspace ORDER BY permission"), values).scalars().all()
    if row.status != "active" or permissions not in (["research:read"], ["research:read", "research:write"]):
        raise SystemExit(71)
    Path(sys.argv[2]).write_text(json.dumps({"revision_id": bytes(row.revision_id).decode(), "write_present": "research:write" in permissions}, separators=(",", ":")))
    os.chmod(sys.argv[2], 0o600)
finally:
    engine.dispose()
PY
docker exec "$CONTROL_PLANE_CONTAINER" cat "$container_dir/current.json" > "$run_dir/current-membership.json"
grant_change="$(docker exec "$CONTROL_PLANE_CONTAINER" liquent-membership-management new-change-id)"
current_revision="$(jq -er '.revision_id' "$run_dir/current-membership.json")"
jq --arg change "$grant_change" --arg revision "$current_revision" \
  '.change_id=$change | .expected_revision=$revision | .status="active" | .permissions=["research:read","research:write"]' \
  "$MEMBERSHIP_BASE_REQUEST" > "$run_dir/grant-request.json"
chmod 0600 "$run_dir"/*.json
if [[ "$(jq -r '.write_present' "$run_dir/current-membership.json")" == true ]]; then
  cp "$run_dir/current-membership.json" "$run_dir/grant-result.json"
else
  apply_membership "$run_dir/grant-request.json" grant
fi
grant_applied=1

put_in_container "$run_dir/grant-request.json" "$container_dir/session-request.json"
docker exec -i "$CONTROL_PLANE_CONTAINER" python - "$container_dir/session-request.json" "$container_dir/session.json" "$DATABASE_URL_SECRET" <<'PY'
import json, os, sys
from pathlib import Path
from sqlalchemy import create_engine, text
request = json.loads(Path(sys.argv[1]).read_text())
engine = create_engine(Path(sys.argv[3]).read_text().strip())
try:
    with engine.connect() as connection:
        row = connection.execute(text("SELECT session_id,csrf_token FROM browser_sessions WHERE user_id=:user_id AND revoked_at IS NULL AND expires_at>CURRENT_TIMESTAMP ORDER BY expires_at DESC LIMIT 1"), {"user_id": request["target_user_id"].encode()}).one_or_none()
    if row is None: raise SystemExit(42)
    Path(sys.argv[2]).write_text(json.dumps({"session_id": bytes(row.session_id).decode(), "csrf_token": bytes(row.csrf_token).decode()}, separators=(",", ":")))
    os.chmod(sys.argv[2], 0o600)
finally:
    engine.dispose()
PY
docker exec "$CONTROL_PLANE_CONTAINER" cat "$container_dir/session.json" > "$run_dir/session.json"
session_id="$(jq -er '.session_id' "$run_dir/session.json")"; csrf_token="$(jq -er '.csrf_token' "$run_dir/session.json")"
printf '# Netscape HTTP Cookie File\n%s\tFALSE\t/\tTRUE\t0\tliquent_session\t%s\n' "${STAGING_ORIGIN#https://}" "$session_id" > "$run_dir/cookies.txt"
printf 'Content-Type: application/json\nX-CSRF-Token: %s\n' "$csrf_token" > "$run_dir/headers.txt"

request_job_id="staging-proof-$(date -u +%Y%m%dT%H%M%SZ)"
experiment_id="${request_job_id}-experiment"
workspace_id="$(jq -er '.workspace_id' "$run_dir/grant-request.json")"
jq -n --arg job "$request_job_id" --arg experiment "$experiment_id" --arg workspace "$workspace_id" '{job_id:$job,experiment_id:$experiment,workspace_id:$workspace,title:"Staging synthetic OHLCV proof",dataset_ref:"staging-synthetic-ohlcv.csv",dataset_fingerprint:"sha256:b455a6bb9246b5da73c59219fe3489126bd59cedb9f678e269d95311a1005475",strategy_version_id:"mid-breakout-v0",strategy_parameters:{lookback_bars:1,stop_distance_pct:0.05,min_strength:0.0,allow_short:true},risk_parameters:{initial_equity:1000.0,max_position_size:10.0,max_total_exposure:100.0,risk_per_trade:5.0,max_daily_drawdown:1000.0,sizing_mode:"absolute"},cost_parameters:{fee_rate:0.0,spread:0.0,slippage:0.0}}' > "$run_dir/job-request.json"

start_status="$(curl -sS -o "$run_dir/start-response.json" -w '%{http_code}' --cookie "$run_dir/cookies.txt" --header @"$run_dir/headers.txt" --data @"$run_dir/job-request.json" "$STAGING_ORIGIN/v1/research/jobs")"
[[ "$start_status" == 202 ]]
durable_job_id="$(jq -er '.job_id' "$run_dir/start-response.json")"; [[ "$durable_job_id" != "$request_job_id" ]]
job_status=queued
for _ in $(seq 1 45); do
  [[ "$(curl -sS -o "$run_dir/job-status.json" -w '%{http_code}' --cookie "$run_dir/cookies.txt" "$STAGING_ORIGIN/v1/research/jobs/$durable_job_id")" == 200 ]]
  job_status="$(jq -er '.status' "$run_dir/job-status.json")"
  case "$job_status" in succeeded|failed|invalidated|cancelled) break;; esac
  sleep 1
done
[[ "$job_status" == succeeded ]]
[[ "$(curl -sS -o "$run_dir/job-evidence.json" -w '%{http_code}' --cookie "$run_dir/cookies.txt" "$STAGING_ORIGIN/v1/research/jobs/$durable_job_id/evidence")" == 200 ]]
jq -e 'type == "object" and length > 0' "$run_dir/job-evidence.json" >/dev/null

put_in_container "$run_dir/job-request.json" "$container_dir/job-request.json"
docker exec -i "$CONTROL_PLANE_CONTAINER" python - "$durable_job_id" "$container_dir/outcome.json" "$DATABASE_URL_SECRET" <<'PY'
import json, os, sys
from pathlib import Path
from sqlalchemy import create_engine, text
engine = create_engine(Path(sys.argv[3]).read_text().strip())
try:
    with engine.connect() as connection:
        row = connection.execute(text("SELECT artifact_key,artifact_sha256,artifact_size_bytes FROM research_job_outcomes WHERE job_id=:job AND kind='succeeded'"), {"job": sys.argv[1].encode()}).one()
        claims = connection.scalar(text("SELECT count(*) FROM research_job_claims WHERE job_id=:job"), {"job": sys.argv[1].encode()})
        outcomes = connection.scalar(text("SELECT count(*) FROM research_job_outcomes WHERE job_id=:job"), {"job": sys.argv[1].encode()})
    Path(sys.argv[2]).write_text(json.dumps({"artifact_key":row.artifact_key,"artifact_sha256":row.artifact_sha256,"artifact_size_bytes":row.artifact_size_bytes,"claim_count":claims,"outcome_count":outcomes}, separators=(",", ":")))
    os.chmod(sys.argv[2], 0o600)
finally: engine.dispose()
PY
docker exec "$CONTROL_PLANE_CONTAINER" cat "$container_dir/outcome.json" | docker exec -i "$RESEARCH_WORKER_CONTAINER" /bin/sh -c 'umask 077; cat > /tmp/research-proof-outcome.json'
docker exec -i "$RESEARCH_WORKER_CONTAINER" python - /tmp/research-proof-outcome.json "$ARTIFACT_ROOT" <<'PY'
import hashlib, json, sys
from pathlib import Path
value=json.loads(Path(sys.argv[1]).read_text()); root=Path(sys.argv[2]).resolve(strict=True); artifact=(root/value["artifact_key"]).resolve(strict=True)
if root not in artifact.parents or not artifact.is_file(): raise SystemExit(51)
content=artifact.read_bytes()
if hashlib.sha256(content).hexdigest()!=value["artifact_sha256"] or len(content)!=value["artifact_size_bytes"]: raise SystemExit(52)
if value["claim_count"]!=1 or value["outcome_count"]!=1: raise SystemExit(54)
PY
docker exec "$RESEARCH_WORKER_CONTAINER" rm -f /tmp/research-proof-outcome.json

revoke_write
jq --arg job "${request_job_id}-denied" --arg experiment "${experiment_id}-denied" '.job_id=$job | .experiment_id=$experiment' "$run_dir/job-request.json" > "$run_dir/denied-request.json"
denied_status="$(curl -sS -o "$run_dir/denied-response.json" -w '%{http_code}' --cookie "$run_dir/cookies.txt" --header @"$run_dir/headers.txt" --data @"$run_dir/denied-request.json" "$STAGING_ORIGIN/v1/research/jobs")"
[[ "$denied_status" == 403 && "$(jq -r '.detail' "$run_dir/denied-response.json")" == permission_denied ]]
printf 'job_id=%s\nwrite_permission=revoked\npost_revocation_submission=http_403_permission_denied\nevidence_directory=%s\n' "$durable_job_id" "$run_dir"
