variable "snowflake_account" {
  type        = string
  description = "Snowflake account identifier."
}

variable "snowflake_user" {
  type        = string
  description = "Snowflake user used by Terraform."
}

variable "snowflake_password" {
  type        = string
  description = "Snowflake password used by Terraform."
  sensitive   = true
}

variable "snowflake_role" {
  type        = string
  description = "Snowflake role used by Terraform."
  default     = "ACCOUNTADMIN"
}

variable "database_name" {
  type        = string
  description = "Main analytics database."
  default     = "HOLIDAY_ITINERARY"
}

variable "warehouse_name" {
  type        = string
  description = "Warehouse used by dbt transformations."
  default     = "TRANSFORMING_WH"
}

variable "analytics_schema" {
  type        = string
  description = "Schema for dbt analytics models."
  default     = "ANALYTICS"
}
