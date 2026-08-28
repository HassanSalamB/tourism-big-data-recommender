#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TEST_ROOT=$(mktemp -d)
FAKE_BIN="$TEST_ROOT/bin"
DOCKER_LOG="$TEST_ROOT/docker.log"
CURL_LOG="$TEST_ROOT/curl.log"
ENV_FILE="$TEST_ROOT/platform.env"
BACKUP_DIR="$TEST_ROOT/backups"

cleanup() {
  if command -v trash >/dev/null 2>&1; then
    trash "$TEST_ROOT"
  fi
}
trap cleanup EXIT

mkdir -p "$FAKE_BIN"

cat > "$FAKE_BIN/docker" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$FAKE_DOCKER_LOG"
if [[ "$*" == *"pg_dump"* ]]; then
  printf 'logical backup data\n'
fi
EOF

cat > "$FAKE_BIN/curl" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$FAKE_CURL_LOG"
EOF

chmod +x "$FAKE_BIN/docker" "$FAKE_BIN/curl"

cat > "$ENV_FILE" <<EOF
APP_IMAGE=ghcr.io/example/holiday-itinerary:0123456789abcdef
AIRFLOW_IMAGE=ghcr.io/example/holiday-itinerary-airflow:0123456789abcdef
CLOUDFLARE_TUNNEL_TOKEN=test-only-token
PUBLIC_BIND_ADDRESS=127.0.0.1
FASTAPI_PORT=8000
STREAMLIT_PORT=8501
AIRFLOW_PORT=8088
KAFKA_UI_PORT=8090
SPARK_UI_PORT=8080
NEO4J_BROWSER_PORT=7474
PROMETHEUS_PORT=9090
ALERTMANAGER_PORT=9093
GRAFANA_PORT=3000
ADMINER_PORT=5050
BACKUP_DIRECTORY=$BACKUP_DIR
DB_USER=admin
DB_PASSWORD=test-only
DB_NAME=holiday_db
EOF

export PATH="$FAKE_BIN:$PATH"
export FAKE_DOCKER_LOG="$DOCKER_LOG"
export FAKE_CURL_LOG="$CURL_LOG"
export COMPOSE_ENV_FILE="$ENV_FILE"

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

assert_log_contains() {
  local file=$1
  local expected=$2
  grep -F -- "$expected" "$file" >/dev/null || fail "expected '$expected' in $file"
}

"$REPO_ROOT/scripts/proxmox/deploy.sh" --check-only
assert_log_contains "$DOCKER_LOG" "compose --env-file $ENV_FILE"
assert_log_contains "$DOCKER_LOG" "--profile tunnel config --quiet"
if grep -F -- " pull" "$DOCKER_LOG" >/dev/null; then
  fail "check-only deployment pulled images"
fi

: > "$DOCKER_LOG"
"$REPO_ROOT/scripts/proxmox/deploy.sh" --skip-healthcheck
assert_log_contains "$DOCKER_LOG" "pull"
assert_log_contains "$DOCKER_LOG" "run --rm airflow-init"
assert_log_contains "$DOCKER_LOG" "up -d --remove-orphans"

"$REPO_ROOT/scripts/proxmox/healthcheck.sh"
assert_log_contains "$CURL_LOG" "http://127.0.0.1:8000/health"
assert_log_contains "$CURL_LOG" "http://127.0.0.1:8501/_stcore/health"
assert_log_contains "$CURL_LOG" "http://127.0.0.1:3000/api/health"

"$REPO_ROOT/scripts/proxmox/backup.sh"
backup_path=$(find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)
[[ -n "$backup_path" ]] || fail "backup directory was not created"
[[ -s "$backup_path/holiday-db.sql" ]] || fail "application database backup is missing"
[[ -s "$backup_path/airflow-db.sql" ]] || fail "Airflow database backup is missing"
[[ -s "$backup_path/configuration.tar.gz" ]] || fail "configuration backup is missing"
[[ -s "$backup_path/SHA256SUMS" ]] || fail "backup checksums are missing"

if COMPOSE_ENV_FILE="$TEST_ROOT/missing.env" "$REPO_ROOT/scripts/proxmox/deploy.sh" --check-only >/dev/null 2>&1; then
  fail "deployment accepted a missing environment file"
fi

printf 'Proxmox script tests passed.\n'
