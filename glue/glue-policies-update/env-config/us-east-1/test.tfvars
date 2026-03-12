job_name             = "usmg-test-datalake-glue-job"
glue_connection_name = "usmg-test-datalake-glue-conn"

script_location = "s3://replace-me-test-artifacts/glue/test/job.py"
temp_dir        = "s3://replace-me-test-artifacts/glue/test/temp/"

cross_account_bucket_name       = "silverton-maa-purpose-data-test"
cross_account_bucket_account_id = "222222222222"
cross_account_bucket_prefixes   = ["gedp_external_tables/export_feed_copies/usmg_mto_oss"]

cross_account_access_mode       = "read"

# Optional extras
# kms_key_arns = ["arn:aws:kms:us-east-1:222222222222:key/replace-me"]
# secret_arns  = ["arn:aws:secretsmanager:us-east-1:222222222222:secret:replace-me"]
# secret_arn_for_connection = "arn:aws:secretsmanager:us-east-1:222222222222:secret:replace-me"
