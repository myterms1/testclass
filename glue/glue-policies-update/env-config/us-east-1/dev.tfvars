job_name             = "usmg-dev-datalake-glue-job"
glue_connection_name = "usmg-dev-datalake-glue-conn"

# Provide either:
# 1) an existing script location in S3, or
# 2) script_bucket_name + local_script_path to upload from this repo.
script_location = "s3://replace-me-dev-artifacts/glue/dev/job.py"
# script_bucket_name = "replace-me-dev-artifacts"
# local_script_path  = "scripts/job.py"

temp_dir = "s3://replace-me-dev-artifacts/glue/dev/temp/"

cross_account_bucket_name       = "silverton-maa-purpose-data-dev"
cross_account_bucket_account_id = "111111111111"
cross_account_bucket_prefixes   = ["gedp_external_tables/export_feed_copies/usmg_mto_oss"]

cross_account_access_mode       = "read"

# Optional extras
# kms_key_arns = ["arn:aws:kms:us-east-1:111111111111:key/replace-me"]
# secret_arns  = ["arn:aws:secretsmanager:us-east-1:111111111111:secret:replace-me"]
# secret_arn_for_connection = "arn:aws:secretsmanager:us-east-1:111111111111:secret:replace-me"
