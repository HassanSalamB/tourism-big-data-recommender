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

# Default command is a lightweight API process; Compose overrides this for each service.
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

# FastAPI and Streamlit dashboard ports.
EXPOSE 8000
EXPOSE 8501
