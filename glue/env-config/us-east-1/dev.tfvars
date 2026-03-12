job_name             = "usmg-dev-datalake-glue-job"
glue_connection_name = "usmg-dev-datalake-glue-conn"

# Provide either:
# 1) an existing script location in S3, or
# 2) script_bucket_name + local_script_path to upload from this repo.
# Glue script uploads default to the shared-resources artifact bucket:
# s3://usmg-dev-datamart-artifact-bucket/glue/scripts/job.py
# temp_dir defaults to:
# s3://usmg-dev-datamart-artifact-bucket/glue/temp/

cross_account_bucket_name       = "replace-me-dev-datalake"
cross_account_bucket_account_id = "111111111111"
cross_account_bucket_prefixes   = ["incoming/dev", "processed/dev"]

# Optional extras
# kms_key_arns = ["arn:aws:kms:us-east-1:111111111111:key/replace-me"]
# secret_arns  = ["arn:aws:secretsmanager:us-east-1:111111111111:secret:replace-me"]
# secret_arn_for_connection = "arn:aws:secretsmanager:us-east-1:111111111111:secret:replace-me"
