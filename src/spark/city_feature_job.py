"""Build city-level feature aggregates with Spark."""

from __future__ import annotations

import os

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def main() -> None:
    input_path = os.getenv(
        "SPARK_PLACES_PARQUET",
        "/opt/holiday/data/silver/parquet/places.parquet",
    )
    output_path = os.getenv(
        "SPARK_CITY_FEATURES_OUT",
        "/opt/holiday/data/gold/spark/city_features",
    )
    master_url = os.getenv("SPARK_MASTER_URL", "spark://spark-master:7077")

    spark = (
        SparkSession.builder.appName("holiday-city-feature-job")
        .master(master_url)
        .config("spark.driver.memory", os.getenv("SPARK_DRIVER_MEMORY", "1g"))
        .config("spark.executor.memory", os.getenv("SPARK_EXECUTOR_MEMORY", "1g"))
        .config("spark.executor.cores", os.getenv("SPARK_EXECUTOR_CORES", "1"))
        .config(
            "spark.sql.shuffle.partitions",
            os.getenv("SPARK_SQL_SHUFFLE_PARTITIONS", "8"),
        )
        .getOrCreate()
    )
    try:
        places = spark.read.parquet(input_path)
        features = (
            places.where(F.col("city").isNotNull())
            .groupBy("city")
            .agg(
                F.count("*").alias("place_count"),
                F.countDistinct("region").alias("region_count"),
                F.avg("lat").alias("avg_lat"),
                F.avg("lon").alias("avg_lon"),
            )
        )
        features.write.mode("overwrite").parquet(output_path)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
