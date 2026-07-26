#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

offline=0
[[ "${1:-}" == "--offline" ]] && { offline=1; shift; }
[[ "$#" == 4 ]] || deploy_die "usage: preflight-initial-staging.sh [--offline] IMAGE RELEASE-MANIFEST BACKUP-EVIDENCE INITIAL-CONFIG"
image="$1"; release_manifest="$2"; backup_evidence="$3"; initial_config="$4"

deploy_load_config
deploy_validate_evidence "$image" "$release_manifest" "$backup_evidence"
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
  command -v getent >/dev/null || deploy_die "getent is required for DNS preflight"
  getent ahostsv4 "$STAGING_HOST" | awk '{print $1}' | grep -Fxq "$EXPECTED_IPV4" || \
    deploy_die "staging DNS does not resolve to EXPECTED_IPV4"
fi

deploy_info "initial staging preflight valid; no mutation performed"
