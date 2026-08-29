# Proxmox Deployment Runbook

This runbook deploys the complete tourism platform to one Ubuntu VM on a Proxmox host. It prepares a future deployment; it does not mean a Proxmox server or backend is currently live.

## Architecture boundary

- Render remains the always-available public portfolio and curated Streamlit sample.
- The Proxmox VM runs the full Airflow, Kafka, Spark, dbt, database, API, and observability stack.
- Cloudflare Tunnel is the only public ingress to the VM.
- Database, broker, and Docker daemon ports are never published publicly.
- Administrative interfaces must be protected with Cloudflare Access.

## 1. Create the VM

Create an Ubuntu Server 24.04 LTS VM with approximately:

| Resource | Starting allocation |
|---|---:|
| vCPU | 6 |
| RAM | 16 GB |
| Disk | 120 GB |

Use a private LAN address, enable the QEMU guest agent, and take a Proxmox snapshot before major upgrades. A snapshot is not a substitute for database backups.

## 2. Prepare Ubuntu

Create a non-root deployment user, add an SSH key, disable password-based SSH after confirming key access, install security updates, and install Docker Engine with the Compose plugin from Docker's official Ubuntu repository.

Allow only SSH from a trusted network. The release configuration binds web interfaces to `127.0.0.1`, so no dashboard ports need firewall exposure.

Verify the host:

```bash
docker version
docker compose version
```

## 3. Obtain the release

Clone or copy the repository to the VM. For private GHCR packages, authenticate with a GitHub token that has only `read:packages` permission:

```bash
echo "$GHCR_READ_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USER --password-stdin
```

Do not save the token in this repository.

## 4. Configure secrets

```bash
cp distribution/.env.example distribution/.env
chmod 600 distribution/.env
```

Edit `distribution/.env` on the VM only. At minimum:

- Replace `APP_IMAGE` and `AIRFLOW_IMAGE` with GHCR images tagged by a real commit SHA.
- Replace every password and secret placeholder with a different random value.
- Supply the DATAtourisme credential if live ingestion is enabled.
- Set `CLOUDFLARE_TUNNEL_TOKEN` after creating the tunnel.
- Set `BACKUP_DIRECTORY` to storage with enough capacity.

Generate secrets locally on the VM, for example:

```bash
openssl rand -hex 32
```

Never add `distribution/.env` to Git or paste its values into issues, screenshots, or documentation.

## 5. Configure Cloudflare

Add the domain to Cloudflare, create a remotely managed tunnel, and map hostnames to Docker service URLs. Use `distribution/cloudflared/config.yml.example` as a naming guide; the token-based container does not require that example file at runtime.

Recommended access policy:

| Destination | Policy |
|---|---|
| Streamlit | Public |
| FastAPI documentation/read-only routes | Public with rate limiting |
| Curated Grafana dashboard | Public Viewer only |
| Airflow, Kafka UI, Spark, Prometheus, Neo4j, Adminer | Cloudflare Access login required |

Do not tunnel the Proxmox interface, SSH, PostgreSQL, Kafka broker, Neo4j Bolt, or Docker TCP socket.

## 6. Validate and deploy

First validate the environment and rendered Compose model without starting anything:

```bash
scripts/proxmox/deploy.sh --check-only
```

Then deploy:

```bash
scripts/proxmox/deploy.sh
```

The deploy script validates immutable image tags, pulls images, initializes Airflow, starts the stack, and checks local endpoints. To inspect state:

```bash
SERVICE_ENV_FILE="$PWD/distribution/.env" docker compose \
  --env-file distribution/.env \
  -f distribution/compose.release.yml \
  --profile tunnel ps
```

## 7. Connect the portfolio

Keep `BACKEND_ENVIRONMENT_STATUS=recorded` on Render until every intended route has been verified. Then configure only the HTTPS URLs that should appear in the portfolio:

```text
SERVICE_STREAMLIT_URL
SERVICE_FASTAPI_URL
SERVICE_AIRFLOW_URL
SERVICE_KAFKA_UI_URL
SERVICE_SPARK_URL
SERVICE_GRAFANA_URL
SERVICE_PROMETHEUS_URL
SERVICE_NEO4J_URL
SERVICE_ADMINER_URL
BACKEND_ENVIRONMENT_STATUS=live
```

Use `maintenance` during planned downtime. The portfolio retains recorded evidence in all three states.

## 8. Back up and restore

Create an on-demand backup:

```bash
scripts/proxmox/backup.sh
```

The script writes application and Airflow PostgreSQL dumps, non-secret release configuration, and SHA-256 checksums. Schedule it nightly with systemd or cron and copy encrypted backups outside the VM. Neo4j, Grafana runtime state, and other Docker volumes require an additional tested volume-backup procedure before they contain irreplaceable production data.

Test SQL restoration into disposable databases before relying on the backup:

```bash
docker compose --env-file distribution/.env -f distribution/compose.release.yml exec -T postgres \
  psql --username YOUR_DB_USER --dbname YOUR_TEST_DATABASE < holiday-db.sql
```

Do not restore over the active database without a separate maintenance and rollback plan.

## 9. Update or stop

To deploy a new release, replace both image tags with the new commit SHA and rerun `scripts/proxmox/deploy.sh`. Back up first.

Stop containers without deleting data:

```bash
SERVICE_ENV_FILE="$PWD/distribution/.env" docker compose \
  --env-file distribution/.env \
  -f distribution/compose.release.yml \
  --profile tunnel down
```

Never add `-v` unless permanent deletion of all named-volume data is explicitly intended and a tested backup exists.

## Go-live checklist

- `scripts/proxmox/deploy.sh --check-only` succeeds.
- `scripts/proxmox/healthcheck.sh` succeeds on the VM.
- The Airflow DAG completes Bronze, Silver, Gold, Spark, graph, and dbt stages.
- Kafka UI receives an itinerary event.
- Prometheus targets are healthy and Grafana displays data.
- Anonymous requests cannot reach administrative dashboards.
- Render still works when the VM or tunnel is stopped.
- A backup has been restored successfully into a disposable test database.
