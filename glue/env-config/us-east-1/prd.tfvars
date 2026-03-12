job_name             = "usmg-prd-datalake-glue-job"
glue_connection_name = "usmg-prd-datalake-glue-conn"

script_location = "s3://replace-me-prd-artifacts/glue/prd/job.py"
temp_dir        = "s3://replace-me-prd-artifacts/glue/prd/temp/"

cross_account_bucket_name       = "replace-me-prd-datalake"
cross_account_bucket_account_id = "333333333333"
cross_account_bucket_prefixes   = ["incoming/prd", "processed/prd"]

# Optional extras
# kms_key_arns = ["arn:aws:kms:us-east-1:333333333333:key/replace-me"]
# secret_arns  = ["arn:aws:secretsmanager:us-east-1:333333333333:secret:replace-me"]
# secret_arn_for_connection = "arn:aws:secretsmanager:us-east-1:333333333333:secret:replace-me"
