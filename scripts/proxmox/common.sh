#!/usr/bin/env bash

set -euo pipefail

PROXMOX_SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$PROXMOX_SCRIPT_DIR/../.." && pwd)
COMPOSE_FILE=${COMPOSE_FILE:-"$REPO_ROOT/distribution/compose.release.yml"}
COMPOSE_ENV_FILE=${COMPOSE_ENV_FILE:-"$REPO_ROOT/distribution/.env"}

die() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

require_file() {
  [[ -f "$1" ]] || die "required file not found: $1"
}

load_platform_environment() {
  require_file "$COMPOSE_ENV_FILE"
  set -a
  # shellcheck disable=SC1090
  source "$COMPOSE_ENV_FILE"
  set +a
}

require_runtime_configuration() {
  local variable
  for variable in APP_IMAGE AIRFLOW_IMAGE; do
    [[ -n "${!variable:-}" ]] || die "$variable is required in $COMPOSE_ENV_FILE"
    [[ "${!variable}" != *":commit-sha" ]] || die "$variable still uses the example commit-sha tag"
    [[ "${!variable}" =~ :[0-9a-fA-F]{7,64}$ ]] || die "$variable must use an immutable Git commit SHA tag"
  done

  [[ -n "${CLOUDFLARE_TUNNEL_TOKEN:-}" ]] || die "CLOUDFLARE_TUNNEL_TOKEN is required"
  [[ "$CLOUDFLARE_TUNNEL_TOKEN" != "set-on-the-proxmox-vm-only" ]] || die "replace the example Cloudflare tunnel token"
}

compose() {
  SERVICE_ENV_FILE="$COMPOSE_ENV_FILE" docker compose \
    --env-file "$COMPOSE_ENV_FILE" \
    -f "$COMPOSE_FILE" \
    --profile tunnel \
    "$@"
}
