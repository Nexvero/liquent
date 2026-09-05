#!/usr/bin/env bash
set -Eeuo pipefail

source_dir="${RENEWED_LINEAGE:-/etc/letsencrypt/live/staging.liquent.ai}"
target_dir="${LIQUENT_EDGE_CERT_DIR:-/opt/liquent/edge/certs}"
edge_compose="${LIQUENT_EDGE_COMPOSE_FILE:-/opt/liquent/edge/compose.edge.yaml}"
edge_env="${LIQUENT_EDGE_ENV_FILE:-/opt/liquent/edge/edge.env}"
host=staging.liquent.ai

[[ "$(id -u)" == 0 ]] || { echo "certificate install requires root" >&2; exit 1; }
for name in fullchain.pem privkey.pem; do
  [[ -f "$source_dir/$name" && -r "$source_dir/$name" ]] || {
    echo "certificate source unavailable" >&2
    exit 1
  }
done

openssl x509 -in "$source_dir/fullchain.pem" -noout -checkhost "$host" >/dev/null 2>&1 || {
  echo "certificate hostname mismatch" >&2
  exit 1
}
cert_key="$(openssl x509 -in "$source_dir/fullchain.pem" -pubkey -noout | openssl pkey -pubin -outform DER 2>/dev/null | openssl sha256)"
private_key="$(openssl pkey -in "$source_dir/privkey.pem" -pubout -outform DER 2>/dev/null | openssl sha256)"
[[ "$cert_key" == "$private_key" ]] || { echo "certificate key mismatch" >&2; exit 1; }

install -d -o root -g root -m 0700 "$target_dir"
fullchain_tmp="$(mktemp "$target_dir/.fullchain.pem.XXXXXX")"
private_key_tmp="$(mktemp "$target_dir/.privkey.pem.XXXXXX")"
trap 'rm -f -- "$fullchain_tmp" "$private_key_tmp"' EXIT
install -o root -g root -m 0644 "$source_dir/fullchain.pem" "$fullchain_tmp"
install -o root -g root -m 0600 "$source_dir/privkey.pem" "$private_key_tmp"
mv -f "$fullchain_tmp" "$target_dir/fullchain.pem"
mv -f "$private_key_tmp" "$target_dir/privkey.pem"
trap - EXIT

if [[ -f "$edge_compose" && -f "$edge_env" ]] &&
   docker compose --env-file "$edge_env" --file "$edge_compose" ps --status running --services 2>/dev/null | grep -Fxq edge; then
  docker compose --env-file "$edge_env" --file "$edge_compose" exec -T edge nginx -s reload
fi
