#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

check_only=false
skip_healthcheck=false

usage() {
  printf 'Usage: %s [--check-only] [--skip-healthcheck]\n' "$0"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only) check_only=true ;;
    --skip-healthcheck) skip_healthcheck=true ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; die "unknown option: $1" ;;
  esac
  shift
done

require_command docker
require_file "$COMPOSE_FILE"
load_platform_environment
require_runtime_configuration

compose config --quiet
if [[ "$check_only" == true ]]; then
  printf 'Release configuration is valid.\n'
  exit 0
fi

compose pull
compose run --rm airflow-init
compose up -d --remove-orphans

if [[ "$skip_healthcheck" == false ]]; then
  "$SCRIPT_DIR/healthcheck.sh"
fi

printf 'Platform deployment completed.\n'
