# Glue Job Module

This module creates the core resources needed for a VPC-enabled AWS Glue job that reads and/or writes a cross-account S3 bucket.

## What it creates

- Glue IAM execution role
- Glue role policy attachments and inline permissions
- Dedicated Glue security group
- Glue network connection
- Glue job
- Optional local script upload to S3
- Output JSON documents for the target bucket policy and target KMS key policy

## What it expects from the existing repo

This repo already centralizes the VPC remote state details in `module/aws/terragrunt.hcl`. The module uses those shared inputs and reads these remote outputs:

- `id`
- `subnets_non_routable_by_az`

The Glue connection automatically chooses the first non-routable subnet unless you override it with `glue_connection_subnet_id`.

## Deployment

```bash
export TF_VAR_env=dev
export TF_VAR_region=us-east-1
terraform init
terraform plan
terraform apply
```

The module's `terragrunt.hcl` already loads:

- `module/aws/common.tfvars`
- `env-config/common.tfvars`
- `env-config/us-east-1/common.tfvars`
- `env-config/us-east-1/<env>.tfvars`

## Cross-account S3

The module grants the Glue role access from the job account side. It also outputs:

- `recommended_cross_account_bucket_policy_json`
- `recommended_cross_account_kms_policy_json`

Those JSON documents should be applied in the bucket-owning account when you want Terraform-managed bucket/KMS policy updates there.

## KMS and secrets

- Set `kms_key_arns` only when the script bucket, temp bucket, target bucket, or referenced secret uses SSE-KMS / customer-managed keys.
- Set `secret_arns` and `secret_arn_for_connection` only when the job or connection needs Secrets Manager.

## Example tfvars layout

- `env-config/common.tfvars` for shared Glue defaults
- `env-config/us-east-1/dev.tfvars`
- `env-config/us-east-1/test.tfvars`
- `env-config/us-east-1/prd.tfvars`


## Default script and temp paths

Unless you override them, this module now uses the shared-resources artifact bucket naming pattern already present in the repo:

- Script bucket: `usmg-<env>-datamart-artifact-bucket`
- Script object: `glue/scripts/job.py`
- Temp dir: `s3://usmg-<env>-datamart-artifact-bucket/glue/temp/`

The module includes a starter Glue script at `scripts/job.py`, and Terraform uploads it automatically when `local_script_path` exists.
