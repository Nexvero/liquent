#!/usr/bin/env bash
set -Eeuo pipefail

image="${1:?usage: backup-smoke-test.sh IMAGE}"
fixture="$(mktemp -d)"
host_uid="$(id -u)"
host_gid="$(id -g)"
cleanup() {
  docker run --rm --user 0:0 \
    --volume "$fixture:/fixture" \
    --entrypoint chown "$image" -R "${host_uid}:${host_gid}" /fixture \
    >/dev/null 2>&1 || true
  rm -rf -- "$fixture"
}
trap cleanup EXIT INT TERM

mkdir -p "$fixture/secrets"
for name in restic_password ovh_access_key ovh_secret_key pgpass; do
  printf 'smoke-only\n' > "$fixture/secrets/$name"
  chmod 0600 "$fixture/secrets/$name"
done
cat > "$fixture/backup.env" <<'EOF'
RESTIC_REPOSITORY=s3:https://s3.example.invalid/bucket/liquent
RESTIC_PASSWORD_FILE=/run/secrets/restic_password
OVH_ACCESS_KEY_FILE=/run/secrets/ovh_access_key
OVH_SECRET_KEY_FILE=/run/secrets/ovh_secret_key
PGPASSFILE=/run/secrets/pgpass
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=liquent
POSTGRES_USER=liquent
BACKUP_DATABASE_DIR=/backup-input/database
ARTIFACT_ROOT=/backup-input/artifacts
BACKUP_HOST_ID=liquent-smoke
LIQUENT_MIGRATION_HEAD=smoke-only
EOF
chmod 0600 "$fixture/backup.env"

docker run --rm --user 0:0 \
  --volume "$fixture:/fixture" \
  --entrypoint chown "$image" -R 10001:10001 /fixture

docker run --rm \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --tmpfs /tmp:size=16m,mode=1777 \
  --tmpfs /backup-input/database:size=64m,mode=0700,uid=10001,gid=10001 \
  --tmpfs /backup-input/artifacts:size=64m,mode=0700,uid=10001,gid=10001 \
  --volume "$fixture/backup.env:/run/config/backup.env:ro" \
  --volume "$fixture/secrets:/run/secrets:ro" \
  --env LIQUENT_BACKUP_CONFIG=/run/config/backup.env \
  --entrypoint /bin/sh \
  "$image" -eu -c '
    test "$(id -u):$(id -g)" = "10001:10001"
    command -v pg_dump >/dev/null
    command -v pg_restore >/dev/null
    command -v restic >/dev/null
    pg_dump --version
    restic version
    /opt/liquent/backup/backup.sh --check
  '
