app = "Datalake Glue"

required_tags = {
  "AssetOwner"       = "replace-me@example.com"
  "CostCenter"       = "00000"
  "SecurityReviewID" = "RITM0000000"
  "ServiceNowAS"     = "AS000000"
  "ServiceNowBA"     = "BA00000"
}

optional_tags = {
  "AssignmentGroup" = "MTO Automation and Observability"
}

data_at_rest_tags = {
  "BusinessEntity"         = ""
  "ComplianceDataCategory" = ""
  "DataClassification"     = ""
  "DataSubjectArea"        = ""
  "LineOfBusiness"         = ""
  "processName"            = ""
}

job_description                  = "Glue ETL job for cross-account S3 processing"
glue_connection_description      = "Glue VPC network connection for datalake processing"
glue_version                     = "4.0"
worker_type                      = "G.1X"
number_of_workers                = 2
max_concurrent_runs              = 1
max_retries                      = 0
timeout                          = 60
execution_class                  = "STANDARD"
command_name                     = "glueetl"
job_bookmark_option              = "job-bookmark-disable"
enable_glue_datacatalog          = true
enable_continuous_logging        = true
enable_metrics                   = true
enable_spark_ui                  = false
create_glue_security_group       = true
allowed_https_cidrs              = ["0.0.0.0/0"]
internal_egress_ports            = [5432]
cross_account_access_mode        = "readwrite"
allow_delete_in_target_prefixes  = false
kms_key_arns                     = []
secret_arns                      = []
connections                      = []
default_arguments = {}
non_overridable_arguments = {}
