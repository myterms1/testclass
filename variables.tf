variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
}

variable "description" {
  description = "Description of the Lambda function"
  type        = string
  default     = "A Lambda Function"
}

variable "architectures" {
  description = "Instruction set architecture for the Lambda function"
  type        = list(string)
  default     = ["x86_64"]
}

variable "zip_file" {
  description = "Path to the Lambda deployment package (relative to the module)"
  type        = string
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

variable "memory_size" {
  description = "Memory allocated to the Lambda function (in MB)"
  type        = number
  default     = 256
}

variable "timeout" {
  description = "Execution timeout for the Lambda function (in seconds)"
  type        = number
  default     = 30
}

variable "publish" {
  description = "Whether to publish a new version of the Lambda function"
  type        = bool
  default     = false
}

variable "reserved_concurrent_executions" {
  description = "Number of reserved concurrent executions"
  type        = number
  default     = -1
}

variable "environment_variables" {
  description = "Environment variables for the Lambda function (in map format)"
  type        = map(string)
  default     = {}
}

variable "required_tags" {
  description = "Required tags for resources"
  type        = map(string)
  default     = {}
}

variable "optional_tags" {
  description = "Optional tags for resources"
  type        = map(string)
  default     = {}
}
