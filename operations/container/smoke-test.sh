#!/usr/bin/env bash
set -Eeuo pipefail

image="${1:?usage: smoke-test.sh IMAGE}"
container_name="liquent-smoke-${GITHUB_RUN_ID:-local}-$$"

cleanup() {
  docker rm --force "${container_name}" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

docker run --detach \
  --name "${container_name}" \
  --read-only \
  --tmpfs /tmp:size=64m,mode=1777 \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --env LIQUENT_ENVIRONMENT=ci \
  --env LIQUENT_HTTP_HOST=0.0.0.0 \
  --env LIQUENT_LOG_FORMAT=json \
  "${image}" >/dev/null

for _ in $(seq 1 30); do
  state="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' "${container_name}")"
  case "${state}" in
    healthy)
      docker exec "${container_name}" python -c \
        "import json,urllib.request; assert json.load(urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2))['status'] == 'ok'"
      exit 0
      ;;
    unhealthy)
      docker logs "${container_name}" >&2
      exit 1
      ;;
  esac
  sleep 1
done

docker logs "${container_name}" >&2
echo "container did not become healthy within 30 seconds" >&2
exit 1
