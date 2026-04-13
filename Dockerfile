FROM python:3.12-slim

# Install system dependencies for the Postgres driver (psycopg2)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install libraries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app/src

# Copy the rest of your code
COPY . .

# Default worker: API bronze ingest only. Full DAG: `python3 -m pipeline`
CMD ["python3", "-m", "src.pipeline", "--silver-full"]

# Expose any necessary ports (if applicable)
EXPOSE 8000
