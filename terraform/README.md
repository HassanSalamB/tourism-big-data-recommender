# Terraform Starter

This folder is intentionally separate from the local Docker stack. Use it when the
project is ready to provision cloud resources instead of only running locally.

Recommended targets:

- Snowflake database, warehouse, roles, and schemas for dbt.
- Object storage for raw DATAtourisme ZIPs and Parquet snapshots.
- Managed Kafka or equivalent event streaming service for live feeds.
- Managed Spark service for large batch transformations.
- Secrets manager entries for database, Snowflake, and API credentials.

Example Snowflake configuration lives in `examples/snowflake`.

```bash
cd terraform/examples/snowflake
terraform init
terraform plan
```

Do not commit `.tfvars` files containing real credentials.
