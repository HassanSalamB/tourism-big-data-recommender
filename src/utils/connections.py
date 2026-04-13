"""Connection helpers for Postgres and Neo4j."""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def conn_env():
    """
    Connection using DB_USER, DB_PASSWORD, DB_NAME, DB_HOST, DB_PORT (same as docker-compose `.env`).
    Raises ValueError if any of user, password, dbname, host is missing.
    """
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    dbname = os.getenv("DB_NAME")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    if not all([user, password, dbname, host]):
        # Failing early here makes container/env mistakes clearer than psycopg2's
        # lower-level connection errors.
        raise ValueError(
            "Missing DB_HOST, DB_NAME, DB_USER, and/or DB_PASSWORD. "
            "Set them in `.env` (same as docker-compose)."
        )
    # Every stage shares the same Postgres connection helper so credentials stay in one place.
    return psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=int(port),
    )


def neo4j_env():
    """
    Bolt URL and (user, password) for the graph loader from `.env`:
    - Prefer `NEO4J_URI` (e.g. `bolt://localhost:7687` or `bolt://neo4j:7687` in Compose).
    - Else if `NEO4J_HOST` starts with `bolt://` or `neo4j://`, use it as the full URI (legacy layout).
    - Else build `bolt://{NEO4J_HOST}:{NEO4J_PORT}` (default host `localhost`, port `7687`).
    Also `NEO4J_USER`, `NEO4J_PASSWORD` (defaults `neo4j` / `neo4j`, same as Compose `neo4j` service).
    """
    uri = os.getenv("NEO4J_URI")
    if not uri:
        host = os.getenv("NEO4J_HOST", "localhost")
        if host.startswith("bolt://") or host.startswith("neo4j://"):
            # Support older `.env` files that stored the full Bolt URI in NEO4J_HOST.
            uri = host
        else:
            port = os.getenv("NEO4J_PORT", "7687")
            uri = f"bolt://{host}:{port}"
    # Neo4j defaults match the local Compose service unless overridden in `.env`.
    return (
        uri,
        (
            os.getenv("NEO4J_USER", "neo4j"),
            os.getenv("NEO4J_PASSWORD", "neo4j"),
        ),
    )
