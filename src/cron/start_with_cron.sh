#!/bin/sh
set -e

run_etl() {
    if [ -f /app/.env ]; then
        set -a
        . /app/.env
        set +a
    fi

    cd /app
    PYTHONPATH=/app/src python3 -m src.pipeline --silver-full
}

echo "[Worker] Running ETL immediately, then every hour."
while true; do
    run_etl
    echo "[Worker] ETL run finished. Sleeping for 1 hour..."
    sleep 3600
done
