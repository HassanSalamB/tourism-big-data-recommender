#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

require_command curl
load_platform_environment

bind_address=${PUBLIC_BIND_ADDRESS:-127.0.0.1}
if [[ "$bind_address" == "0.0.0.0" ]]; then
  bind_address=127.0.0.1
fi

check_endpoint() {
  local name=$1
  local url=$2
  curl --fail --silent --show-error \
    --retry 12 --retry-delay 5 --retry-connrefused \
    --max-time 10 "$url" >/dev/null
  printf 'OK  %s\n' "$name"
}

check_endpoint "FastAPI" "http://$bind_address:${FASTAPI_PORT:-8000}/health"
check_endpoint "Streamlit" "http://$bind_address:${STREAMLIT_PORT:-8501}/_stcore/health"
check_endpoint "Airflow" "http://$bind_address:${AIRFLOW_PORT:-8088}/health"
check_endpoint "Kafka UI" "http://$bind_address:${KAFKA_UI_PORT:-8090}/actuator/health"
check_endpoint "Spark" "http://$bind_address:${SPARK_UI_PORT:-8080}/"
check_endpoint "Prometheus" "http://$bind_address:${PROMETHEUS_PORT:-9090}/-/healthy"
check_endpoint "Alertmanager" "http://$bind_address:${ALERTMANAGER_PORT:-9093}/-/healthy"
check_endpoint "Grafana" "http://$bind_address:${GRAFANA_PORT:-3000}/api/health"
check_endpoint "Neo4j Browser" "http://$bind_address:${NEO4J_BROWSER_PORT:-7474}/"
check_endpoint "Adminer" "http://$bind_address:${ADMINER_PORT:-5050}/"

printf 'All local service endpoints are healthy.\n'
