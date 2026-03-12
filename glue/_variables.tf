variable "env" {
  description = "Logical environment name."
  type        = string
}

variable "app" {
  description = "Application name used in tags and descriptions."
  type        = string
}

variable "required_tags" {
  description = "Required AWS tags."
  type        = map(string)
}

variable "optional_tags" {
  description = "Optional AWS tags."
  type        = map(string)
  default     = {}
}

variable "data_at_rest_tags" {
  description = "Data classification tags."
  type        = map(string)
  default     = {}
}

variable "awsRegion" {
  description = "AWS region."
  type        = string
}

variable "moduleName" {
  description = "Module name from terragrunt root inputs."
  type        = string
}

variable "awsAccount" {
  description = "AWS account ID for the current deployment account."
  type        = string
}

variable "vpc_state_file" {
  description = "Remote state key for the VPC stack."
  type        = string
}

variable "tf_state_bucket" {
  description = "Remote state bucket name."
  type        = string
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days."
  type        = number
  default     = 30
}

variable "job_name" {
  description = "Glue job name override. Leave null to use the standard naming convention."
  type        = string
  default     = null
}

variable "job_description" {
  description = "Description for the Glue job."
  type        = string
  default     = "Glue ETL job for cross-account S3 processing"
}

variable "glue_connection_name" {
  description = "Glue connection name override. Leave null to use the standard naming convention."
  type        = string
  default     = null
}

variable "glue_connection_description" {
  description = "Description for the Glue connection."
  type        = string
  default     = "Glue VPC network connection"
}

variable "glue_version" {
  description = "AWS Glue version."
  type        = string
  default     = "4.0"
}

variable "worker_type" {
  description = "Glue worker type."
  type        = string
  default     = "G.1X"
}

variable "number_of_workers" {
  description = "Number of Glue workers."
  type        = number
  default     = 2
}

variable "max_concurrent_runs" {
  description = "Maximum concurrent runs for the Glue job."
  type        = number
  default     = 1
}

variable "max_retries" {
  description = "Maximum retry attempts for the Glue job."
  type        = number
  default     = 0
}

variable "timeout" {
  description = "Glue job timeout in minutes."
  type        = number
  default     = 60
}

variable "execution_class" {
  description = "Glue execution class. FLEX and STANDARD are valid for Spark jobs on supported Glue versions."
  type        = string
  default     = "STANDARD"
}

variable "command_name" {
  description = "Glue command name. Usually glueetl or pythonshell."
  type        = string
  default     = "glueetl"
}

variable "python_version" {
  description = "Python version for Python shell jobs."
  type        = string
  default     = "3"
}

variable "local_script_path" {
  description = "Optional local path, relative to this module, to upload as the Glue script."
  type        = string
  default     = "scripts/job.py"
}

variable "script_bucket_name" {
  description = "Bucket used to store the Glue script when local_script_path is supplied. Defaults to the shared-resources artifact bucket naming pattern."
  type        = string
  default     = null
}

variable "script_s3_key" {
  description = "Object key to use when uploading the local Glue script."
  type        = string
  default     = "glue/scripts/job.py"
}

variable "script_location" {
  description = "Existing Glue script S3 location. Used when not uploading a local script."
  type        = string
  default     = null
}

variable "temp_dir" {
  description = "S3 temp dir for the Glue job. Defaults to the shared-resources artifact bucket under glue/temp/."
  type        = string
  default     = null
}

variable "enable_glue_datacatalog" {
  description = "Whether to add --enable-glue-datacatalog=true to default arguments."
  type        = bool
  default     = true
}

variable "enable_continuous_logging" {
  description = "Whether to enable continuous CloudWatch logging."
  type        = bool
  default     = true
}

variable "enable_metrics" {
  description = "Whether to enable Glue job metrics."
  type        = bool
  default     = true
}

variable "enable_spark_ui" {
  description = "Whether to enable Spark UI."
  type        = bool
  default     = false
}

variable "job_bookmark_option" {
  description = "Glue job bookmark option."
  type        = string
  default     = "job-bookmark-disable"
}

variable "extra_python_files" {
  description = "Optional comma-separated S3 URIs for additional Python files."
  type        = string
  default     = null
}

variable "extra_jars" {
  description = "Optional comma-separated S3 URIs for extra JARs."
  type        = string
  default     = null
}

variable "default_arguments" {
  description = "Additional default arguments for the Glue job."
  type        = map(string)
  default     = {}
}

variable "non_overridable_arguments" {
  description = "Optional non-overridable arguments for the Glue job."
  type        = map(string)
  default     = {}
}

variable "glue_security_configuration" {
  description = "Optional Glue security configuration name."
  type        = string
  default     = null
}

variable "connections" {
  description = "Extra Glue connection names to attach in addition to the module-managed network connection."
  type        = list(string)
  default     = []
}

variable "glue_connection_type" {
  description = "Glue connection type. NETWORK is the default for VPC-only networking."
  type        = string
  default     = "NETWORK"
}

variable "connection_properties" {
  description = "Connection properties for non-NETWORK connection types such as JDBC."
  type        = map(string)
  default     = {}
}

variable "availability_zone" {
  description = "Optional AZ override for the Glue connection. Defaults to the AZ of the selected subnet."
  type        = string
  default     = null
}

variable "glue_connection_subnet_id" {
  description = "Optional subnet ID override for the Glue connection. Defaults to the first non-routable subnet from VPC remote state."
  type        = string
  default     = null
}

variable "create_glue_security_group" {
  description = "Whether to create a dedicated security group for the Glue job and connection."
  type        = bool
  default     = true
}

variable "security_group_ids" {
  description = "Existing security groups to attach to the Glue connection when create_glue_security_group is false, or to append when true."
  type        = list(string)
  default     = []
}

variable "glue_security_group_name" {
  description = "Optional security group name override."
  type        = string
  default     = null
}

variable "allowed_https_cidrs" {
  description = "CIDRs allowed for outbound HTTPS."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "internal_egress_cidrs" {
  description = "CIDRs allowed for internal outbound TCP connectivity. Defaults to the VPC CIDR."
  type        = list(string)
  default     = []
}

variable "internal_egress_ports" {
  description = "Internal outbound TCP ports required by downstream services such as databases."
  type        = list(number)
  default     = [5432]
}

variable "cross_account_bucket_name" {
  description = "Target cross-account S3 bucket name that the Glue job needs to access."
  type        = string
}

variable "cross_account_bucket_prefixes" {
  description = "Optional list of object prefixes inside the target bucket that the Glue role may access."
  type        = list(string)
  default     = []
}

variable "cross_account_access_mode" {
  description = "Access mode for the target cross-account bucket. Valid values are read, write, or readwrite."
  type        = string
  default     = "readwrite"
}

variable "cross_account_bucket_account_id" {
  description = "AWS account ID that owns the target S3 bucket. Used for generated bucket/KMS policy documents."
  type        = string
  default     = null
}

variable "allow_delete_in_target_prefixes" {
  description = "Whether to allow s3:DeleteObject in the target bucket prefixes."
  type        = bool
  default     = false
}

variable "kms_key_arns" {
  description = "Optional KMS key ARNs that the Glue role must use for decrypt/data key operations."
  type        = list(string)
  default     = []
}

variable "kms_via_service_s3_only" {
  description = "Whether to restrict KMS use to S3 via service conditions."
  type        = bool
  default     = true
}

variable "secret_arns" {
  description = "Optional Secrets Manager secret ARNs needed by the Glue job or connection."
  type        = list(string)
  default     = []
}

variable "secret_arn_for_connection" {
  description = "Optional single secret ARN to inject into connection_properties as SECRET_ID for non-NETWORK connection types."
  type        = string
  default     = null
}

variable "additional_policy_json" {
  description = "Optional raw IAM policy JSON to attach as an additional inline policy to the Glue role."
  type        = string
  default     = null
}
