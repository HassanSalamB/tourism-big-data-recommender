resource "snowflake_database" "holiday" {
  name = var.database_name
}

resource "snowflake_warehouse" "transforming" {
  name           = var.warehouse_name
  warehouse_size = "XSMALL"
  auto_suspend   = 60
  auto_resume    = true
}

resource "snowflake_schema" "analytics" {
  database = snowflake_database.holiday.name
  name     = var.analytics_schema
}
