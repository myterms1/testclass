resource "aws_glue_job" "this" {
  name              = local.job_name
  description       = var.job_description
  role_arn          = aws_iam_role.glue.arn
  glue_version      = var.glue_version
  worker_type       = var.worker_type
  number_of_workers = var.number_of_workers
  max_retries       = var.max_retries
  timeout           = var.timeout
  execution_class   = var.execution_class

  execution_property {
    max_concurrent_runs = var.max_concurrent_runs
  }

  command {
    name            = var.command_name
    script_location = local.script_location_effective
    python_version  = var.command_name == "pythonshell" ? var.python_version : null
  }

  connections               = local.connection_names_effective
  default_arguments         = local.default_arguments_effective
  non_overridable_arguments = length(var.non_overridable_arguments) > 0 ? var.non_overridable_arguments : null
  security_configuration    = var.glue_security_configuration

  tags = local.tags

  depends_on = [
    aws_iam_role_policy_attachment.aws_glue_service_role,
    aws_iam_role_policy_attachment.glue_inline
  ]
}
