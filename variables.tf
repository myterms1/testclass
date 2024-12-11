variable "subnet_ids" {
  description = "Subnet IDs that should be associated with the Lambda function"
  type        = list(string)
  default     = []
}

variable "security_group_ids" {
  description = "Security group IDs that should be associated with the Lambda function"
  type        = list(string)
  default     = []
}

variable "kms_key_arn" {
  description = "KMS Key ARN to apply to this function for environment variable encryption"
  type        = string
  default     = null
}

variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
}

variable "filename" {
  description = "Local path to the Lambda package. Mutually exclusive with S3 vars."
  type        = string
  default     = null
}

variable "s3_bucket" {
  description = "S3 bucket for the Lambda deployment package"
  type        = string
  default     = null
}

variable "s3_key" {
  description = "Key of the Lambda deployment package in the S3 bucket"
  type        = string
  default     = null
}

variable "s3_object_version" {
  description = "Version of the Lambda deployment package in the S3 bucket"
  type        = string
  default     = null
}

variable "source_code_hash" {
  description = "Hash of the Lambda deployment package for update detection"
  type        = string
  default     = null
}

variable "layers" {
  description = "List of Lambda Layer Version ARNs"
  type        = list(string)
  default     = []
}

variable "handler" {
  description = "Path to the Lambda function handler"
  type        = string
  default     = "lambda_function.lambda_handler"
}

variable "runtime" {
  description = "Runtime environment for the Lambda function"
  type        = string
  default     = "python3.8"
}

variable "role_arn" {
  description = "ARN of the IAM role to be assigned to the Lambda function"
  type        = string
}

variable "description" {
  description = "Description of the Lambda function"
  type        = string
  default     = "A Generic Lambda Function"
}

variable "memory_size" {
  description = "Memory allocated to the Lambda function (in MB)"
  type        = number
  default     = 256
}

variable "timeout" {
  description = "Timeout for the Lambda function (in seconds)"
  type        = number
  default     = 30
}

variable "publish" {
  description = "Whether to publish a new version of the Lambda function"
  type        = bool
  default     = false
}

variable "provisioned_concurrent_executions" {
  description = "Number of provisioned concurrency executions"
  type        = number
  default     = -1
}

variable "reserved_concurrent_executions" {
  description = "Number of reserved concurrent executions"
  type        = number
  default     = -1
}

variable "tracing_enabled" {
  description = "Whether to enable AWS X-Ray tracing"
  type        = bool
  default     = false
}

variable "tracing_type" {
  description = "Tracing mode for AWS X-Ray (Active or PassThrough)"
  type        = string
  default     = "Active"
}

variable "environment_variables" {
  description = "Environment variables for the Lambda function (in map format)"
  type        = map(string)
  default     = {}
}

variable "log_group_retention_in_days" {
  description = "Retention period for the CloudWatch log group"
  type        = number
  default     = 30
}

variable "splunk_destination_arn" {
  description = "Destination ARN for CloudWatch log subscription (e.g., Splunk)"
  type        = string
  default     = null
}

variable "required_tags" {
  description = "Required tags for resources"
  type = map(string)
  default = {}
}

variable "optional_tags" {
  description = "Optional tags for resources"
  type        = map(string)
  default     = {}
}

variable "triggers" {
  description = "List of trigger configurations for the Lambda function"
  type = list(
    object({
      principal  = string
      source_arn = string
    })
  )
  default = []
}

variable "architectures" {
  description = "Instruction set architecture for your Lambda function"
  default     = ["x86_64"]
  type        = list(string)
}

variable "code_signing_config_arn" {
  description = "ARN for a code signing configuration"
  type        = string
  default     = null
}
