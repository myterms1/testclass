output "glue_job_name" {
  description = "Glue job name."
  value       = aws_glue_job.this.name
}

output "glue_job_arn" {
  description = "Glue job ARN."
  value       = aws_glue_job.this.arn
}

output "glue_role_name" {
  description = "Glue IAM role name."
  value       = aws_iam_role.glue.name
}

output "glue_role_arn" {
  description = "Glue IAM role ARN."
  value       = aws_iam_role.glue.arn
}

output "glue_connection_name" {
  description = "Glue connection name."
  value       = aws_glue_connection.this.name
}

output "glue_security_group_id" {
  description = "Security group created for the Glue job, when enabled."
  value       = var.create_glue_security_group ? aws_security_group.glue[0].id : null
}

output "glue_connection_subnet_id" {
  description = "Subnet used by the Glue connection."
  value       = local.selected_subnet_id
}

output "recommended_cross_account_bucket_policy_json" {
  description = "Bucket-account policy JSON to apply on the target bucket so the Glue role can access it."
  value       = data.aws_iam_policy_document.target_bucket_policy.json
}

output "recommended_cross_account_kms_policy_json" {
  description = "KMS key policy JSON to apply on the target CMK when the target bucket uses SSE-KMS."
  value       = length(var.kms_key_arns) > 0 ? data.aws_iam_policy_document.target_kms_policy.json : null
}

output "script_location" {
  description = "Effective script S3 location used by the Glue job."
  value       = local.script_location_effective
}
