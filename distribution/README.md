# Holiday Itinerary Release Distribution

This folder is the lightweight distribution path for someone who does not want to clone the development repo.

They need:

- Docker Desktop or Docker Engine
- this `distribution/` folder
- `.env` created from `.env.example`
- published Docker images for the app and Airflow runtime

## Images

The GitHub Actions workflow can publish:

```text
DOCKERHUB_USERNAME/holiday-itinerary:<branch-or-sha>
DOCKERHUB_USERNAME/holiday-itinerary-airflow:<branch-or-sha>
```

The app image runs FastAPI and Streamlit. The Airflow image contains the DAGs, dbt project, Spark job, and ETL source code used by Airflow.

## Quick Start

1. Copy the release folder:

```text
compose.release.yml
.env.example
monitoring/
```

2. Create `.env`:

```bash
cp .env.example .env
```

3. Edit these values:

```env
APP_IMAGE=your-dockerhub-username/holiday-itinerary:dev
AIRFLOW_IMAGE=your-dockerhub-username/holiday-itinerary-airflow:dev
DATATOURISME_TOKEN=your_real_token
```

4. Initialize Airflow:

```bash
docker compose -f compose.release.yml up airflow-init
```

5. Start the platform:

```bash
docker compose -f compose.release.yml up -d
```

## Open The UIs

```text
Airflow:    http://localhost:8088  admin / admin
FastAPI:    http://localhost:8000/docs
Streamlit:  http://localhost:8501
Spark UI:   http://localhost:8080
Neo4j:      http://localhost:7474
Adminer:    http://localhost:5050
Prometheus: http://localhost:9090
Grafana:    http://localhost:3000  admin / admin
Kafka UI:   http://localhost:8090
```

## Stop

```bash
docker compose -f compose.release.yml down
```

Remove volumes and reset all databases:

```bash
docker compose -f compose.release.yml down -v
```
