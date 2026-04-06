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

# Copy the rest of your code
COPY . .

# Run the ingestion script by default
CMD ["sh", "-c", "python3 src/ingestion/extractapi_bronze.py"]

# Expose any necessary ports (if applicable)
EXPOSE 8000
