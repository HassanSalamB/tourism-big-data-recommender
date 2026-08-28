#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

require_command docker
require_command tar
load_platform_environment

backup_root=${BACKUP_DIRECTORY:-"$REPO_ROOT/backups"}
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
backup_path="$backup_root/$timestamp"
mkdir -p "$backup_path"

compose exec -T postgres pg_dump \
  --username "${DB_USER:?DB_USER is required}" \
  --dbname "${DB_NAME:?DB_NAME is required}" \
  --clean --if-exists > "$backup_path/holiday-db.sql"

compose exec -T airflow-postgres pg_dump \
  --username airflow \
  --dbname airflow \
  --clean --if-exists > "$backup_path/airflow-db.sql"

tar -czf "$backup_path/configuration.tar.gz" -C "$REPO_ROOT" \
  distribution/compose.release.yml \
  distribution/.env.example \
  distribution/cloudflared/config.yml.example \
  distribution/monitoring

(
  cd "$backup_path"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum holiday-db.sql airflow-db.sql configuration.tar.gz > SHA256SUMS
  else
    shasum -a 256 holiday-db.sql airflow-db.sql configuration.tar.gz > SHA256SUMS
  fi
)

printf 'Backup created: %s\n' "$backup_path"
