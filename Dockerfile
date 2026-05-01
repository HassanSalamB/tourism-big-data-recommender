FROM python:3.12-slim

# Install system dependencies for the Postgres driver (psycopg2)
RUN apt-get update && apt-get install -y \
    cron \
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

# Default worker: install hourly cron and run ETL.
CMD ["sh", "/app/src/cron/start_with_cron.sh"]

# FastAPI and Streamlit dashboard ports.
EXPOSE 8000
EXPOSE 8501
