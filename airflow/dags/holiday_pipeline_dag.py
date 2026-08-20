from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator


DEFAULT_ARGS = {
    "owner": "holiday-platform",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="holiday_itinerary_pipeline",
    default_args=DEFAULT_ARGS,
    description="Orchestrates DATAtourisme download, change detection, silver, Spark, gold, graph, and dbt stages.",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["holiday", "etl"],
) as dag:
    bronze_download_zip = BashOperator(
        task_id="bronze_download_zip",
        bash_command="cd /opt/holiday && PYTHONUNBUFFERED=1 python -m src.airflow_tasks bronze-download",
    )

    bronze_detect_and_load_changes = BashOperator(
        task_id="bronze_detect_and_load_changes",
        bash_command="cd /opt/holiday && PYTHONUNBUFFERED=1 BRONZE_LOAD_BATCH_SIZE=500 BRONZE_LOAD_PROGRESS_INTERVAL=5000 python -m src.airflow_tasks bronze-load",
    )

    silver = BashOperator(
        task_id="silver_normalize",
        bash_command=(
            "cd /opt/holiday && "
            "PYTHONUNBUFFERED=1 SILVER_BATCH_SIZE=250 SILVER_PARQUET_BATCH_SIZE=2000 "
            "python -m src.pipeline --skip-api --skip-gold-pg --skip-neo4j --silver-full"
        ),
    )

    spark_city_features = BashOperator(
        task_id="spark_city_features",
        bash_command="cd /opt/holiday && python -m src.spark.city_feature_job",
        retries=3,
        retry_delay=timedelta(minutes=3),
        retry_exponential_backoff=True,
    )

    gold_postgres = BashOperator(
        task_id="gold_postgres",
        bash_command="cd /opt/holiday && python -m src.pipeline --skip-api --skip-silver --skip-neo4j",
    )

    neo4j_graph = BashOperator(
        task_id="neo4j_graph",
        bash_command="cd /opt/holiday && python -m src.pipeline --skip-api --skip-silver --skip-gold-pg",
    )

    dbt_marts = BashOperator(
        task_id="dbt_run_and_test",
        bash_command="cd /opt/holiday/dbt && dbt run --profiles-dir . && dbt test --profiles-dir .",
    )

    (
        bronze_download_zip
        >> bronze_detect_and_load_changes
        >> silver
        >> spark_city_features
        >> gold_postgres
        >> neo4j_graph
        >> dbt_marts
    )
