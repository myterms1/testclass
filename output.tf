output "arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.lambda.arn
}

output "invoke_arn" {
  description = "ARN to invoke the Lambda function via API Gateway"
  value       = aws_lambda_function.lambda.invoke_arn
}

output "function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.lambda.function_name
}

output "version" {
  description = "Latest published version of the Lambda function"
  value       = aws_lambda_function.lambda.version
}

output "log_group" {
  description = "Log group created for the Lambda function"
  value       = aws_cloudwatch_log_group.log_group.name
}
