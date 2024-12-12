# Lambda Function
resource "aws_lambda_function" "lambda" {
  function_name = var.function_name
  description   = var.description

  architectures    = var.architectures
  filename         = "${path.module}/source/${var.zip_file}" # Updated to point to the source folder
  source_code_hash = filebase64sha256("${path.module}/source/${var.zip_file}")
  handler          = var.handler
  runtime          = var.runtime
  memory_size      = var.memory_size
  timeout          = var.timeout
  publish          = var.publish
  reserved_concurrent_executions = var.reserved_concurrent_executions

  role = aws_iam_role.lambda_exec_role.arn # Attach the IAM role to Lambda

  # Environment variables
  environment {
    variables = var.environment_variables
  }

  # Add tags
  tags = merge(
    var.required_tags,
    var.optional_tags
  )
}

# Lambda IAM Role
resource "aws_iam_role" "lambda_exec_role" {
  name               = "${var.function_name}-exec-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(
    var.required_tags,
    var.optional_tags
  )
}

# IAM Policy for EKS Access
resource "aws_iam_policy" "eks_access_policy" {
  name   = "${var.function_name}-eks-access-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "eks:DescribeCluster"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach EKS Policy to the Lambda Role
resource "aws_iam_role_policy_attachment" "eks_access_attachment" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.eks_access_policy.arn
}

# Add AWS Lambda Basic Execution Role (CloudWatch Logs Access)
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
