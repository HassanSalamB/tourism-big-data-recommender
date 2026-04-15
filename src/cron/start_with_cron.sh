#!/bin/sh
set -e

# Install cron job from repo-managed cron file.
crontab /app/src/cron/etl.cron

echo "[Cron] Installed ETL schedule from /app/src/cron/etl.cron."
echo "[Cron] Starting cron daemon..."
exec cron -f
