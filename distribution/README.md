# Holiday Itinerary Single Compose File

This example is for users who only want to download one Compose file and run the app from Docker Hub.

## Quick Start

1. Download `compose.release.yml`.

2. Create a `.env` file in the same folder:

```env
APP_IMAGE=your-dockerhub-username/holiday-itinerary:dev

DATATOURISME_TOKEN=your_api_key/your_feed_id

DB_USER=admin
DB_PASSWORD=root
DB_NAME=holiday_db
DB_PORT=5432
DB_HOST=postgres

NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4jpassword
NEO4J_URI=bolt://neo4j:7687
NEO4J_HOST=neo4j
NEO4J_PORT=7687
```

3. Run:

```bash
docker compose -f compose.release.yml up -d
```

4. Open:

```text
http://localhost:8501
```

FastAPI docs:

```text
http://localhost:8000/docs
```

Docker Hub provides the image. Docker Compose runs the containers locally.
