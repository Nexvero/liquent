#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

offline=0
[[ "${1:-}" == "--offline" ]] && { offline=1; shift; }
[[ "$#" == 4 ]] || deploy_die "usage: preflight-initial-staging.sh [--offline] IMAGE RELEASE-MANIFEST BACKUP-EVIDENCE INITIAL-CONFIG"
image="$1"; release_manifest="$2"; backup_evidence="$3"; initial_config="$4"

deploy_load_config
deploy_validate_evidence "$image" "$release_manifest" "$backup_evidence"
# shellcheck disable=SC1090 -- operator-owned image and host-path selection
source "$COMPOSE_ENV_FILE"
[[ "${LIQUENT_APP_IMAGE:-}" == "$image" ]] || deploy_die "configured application image does not match candidate"
[[ "${LIQUENT_SECRETS_DIR:-}" == /* && "$LIQUENT_SECRETS_DIR" != / ]] || \
  deploy_die "LIQUENT_SECRETS_DIR must be a non-root absolute path"
for name in LIQUENT_POSTGRES_IMAGE LIQUENT_PROMETHEUS_IMAGE LIQUENT_GRAFANA_IMAGE; do
  deploy_is_registry_digest_ref "${!name:-}" || deploy_die "infrastructure image must use an immutable digest: $name"
done
runtime_env="$(dirname "$COMPOSE_FILE")/runtime.env"
deploy_require_nonempty_private_file "$runtime_env"
for secret_name in database_url postgres_password; do
  deploy_require_nonempty_private_file "$LIQUENT_SECRETS_DIR/$secret_name"
done
deploy_require_private_file "$initial_config"
# shellcheck disable=SC1090 -- root-owned, permission-checked operator config
source "$initial_config"
for name in STAGING_HOST EXPECTED_IPV4 EDGE_COMPOSE_FILE EDGE_ENV_FILE EDGE_CONFIG_FILE EDGE_CERT_FILE EDGE_KEY_FILE; do
  [[ -n "${!name:-}" ]] || deploy_die "missing initial staging configuration: $name"
done
[[ "$STAGING_HOST" == "staging.liquent.ai" ]] || deploy_die "unexpected staging hostname"
[[ "$EXPECTED_IPV4" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || deploy_die "EXPECTED_IPV4 is invalid"
for path in "$EDGE_COMPOSE_FILE" "$EDGE_ENV_FILE" "$EDGE_CERT_FILE" "$EDGE_KEY_FILE"; do deploy_require_regular_file "$path"; done
deploy_require_private_file "$EDGE_KEY_FILE"
# shellcheck disable=SC1090 -- operator-owned public image selection
source "$EDGE_ENV_FILE"
[[ "${LIQUENT_EDGE_IMAGE:-}" =~ ^nginx@sha256:[0-9a-f]{64}$ ]] || \
  deploy_die "edge image must be an immutable official nginx digest"

for command in jq openssl; do command -v "$command" >/dev/null || deploy_die "missing command: $command"; done
if openssl x509 -help 2>&1 | grep -q -- '-checkhost'; then
  openssl x509 -in "$EDGE_CERT_FILE" -noout -checkhost "$STAGING_HOST" >/dev/null 2>&1 || \
    deploy_die "certificate does not cover staging hostname"
else
  escaped_host="${STAGING_HOST//./\\.}"
  openssl x509 -in "$EDGE_CERT_FILE" -text -noout | \
    grep -Eq "DNS:${escaped_host}([,[:space:]]|$)" || deploy_die "certificate SAN does not cover staging hostname"
fi
cert_key="$(openssl x509 -in "$EDGE_CERT_FILE" -pubkey -noout | openssl pkey -pubin -outform DER 2>/dev/null | openssl sha256)"
private_key="$(openssl pkey -in "$EDGE_KEY_FILE" -pubout -outform DER 2>/dev/null | openssl sha256)"
[[ "$cert_key" == "$private_key" ]] || deploy_die "certificate and private key do not match"

if (( ! offline )); then
  for command in docker getent; do command -v "$command" >/dev/null || deploy_die "missing command: $command"; done
  getent ahostsv4 "$STAGING_HOST" | awk '{print $1}' | grep -Fxq "$EXPECTED_IPV4" || \
    deploy_die "staging DNS does not resolve to EXPECTED_IPV4"
  for root_file in \
    "$COMPOSE_ENV_FILE" \
    "$runtime_env" \
    "$initial_config" \
    "$EDGE_ENV_FILE" \
    "$EDGE_KEY_FILE" \
    "$LIQUENT_SECRETS_DIR/database_url" \
    "$LIQUENT_SECRETS_DIR/postgres_password"; do
    deploy_require_root_owned_file "$root_file"
  done
  for network_spec in \
    liquent_public:false \
    liquent_application:true \
    liquent_data:true \
    liquent_observability:true; do
    network_name="${network_spec%%:*}"
    expected_internal="${network_spec##*:}"
    if ! deploy_validate_network "$network_name" "$expected_internal"; then
      deploy_info "network will be created by confirmed bootstrap: $network_name"
    fi
  done
fi

deploy_info "initial staging preflight valid; no mutation performed"
