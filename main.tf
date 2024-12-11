resource "aws_lambda_function" "lambda" {
  function_name                  = var.function_name
  description                    = var.description
  architectures                  = var.architectures

  # Deployment options
  filename          = var.filename
  s3_bucket         = var.s3_bucket
  s3_key            = var.s3_key
  s3_object_version = var.s3_object_version

  source_code_hash               = var.source_code_hash
  handler                        = var.handler
  runtime                        = var.runtime
  memory_size                    = var.memory_size
  timeout                        = var.timeout
  publish                        = var.publish
  reserved_concurrent_executions = var.reserved_concurrent_executions
  code_signing_config_arn        = var.code_signing_config_arn
  role                           = var.role_arn
  layers                         = var.layers

  environment {
    variables = var.environment_variables
  }

  kms_key_arn = var.kms_key_arn

  tags = merge(
    var.required_tags,
    var.optional_tags
  )

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }

  dynamic "tracing_config" {
    for_each = var.tracing_enabled ? [{}] : []
    content {
      mode = var.tracing_type
    }
  }
}

# Add permissions for triggers (e.g., S3, API Gateway, EventBridge)
resource "aws_lambda_permission" "trigger" {
  count         = length(var.triggers)
  action        = "lambda:InvokeFunction"
  function_name = var.function_name
  principal     = var.triggers[count.index].principal
  source_arn    = var.triggers[count.index].source_arn
}

# Configure CloudWatch log group
resource "aws_cloudwatch_log_group" "log_group" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_group_retention_in_days

  tags = merge(
    var.required_tags,
    var.optional_tags
  )
}

# Optional subscription filter for Splunk or other log destinations
resource "aws_cloudwatch_log_subscription_filter" "splunk_subscription" {
  count           = var.splunk_destination_arn == null ? 0 : 1
  name            = "${var.function_name}-splunk_subscription"
  log_group_name  = aws_cloudwatch_log_group.log_group.name
  filter_pattern  = ""
  destination_arn = var.splunk_destination_arn
}

# Optional provisioned concurrency configuration
resource "aws_lambda_provisioned_concurrency_config" "provisioned_concurrency" {
  count                             = var.publish && var.provisioned_concurrent_executions > -1 ? 1 : 0
  function_name                     = aws_lambda_function.lambda.function_name
  provisioned_concurrent_executions = var.provisioned_concurrent_executions
  qualifier                         = aws_lambda_function.lambda.version
}
