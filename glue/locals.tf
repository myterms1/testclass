locals {
  fullname                = "glue"
  job_name                = coalesce(var.job_name, "usmg-${var.env}-datamart-${local.fullname}-job")
  connection_name         = coalesce(var.glue_connection_name, "usmg-${var.env}-datamart-${local.fullname}-conn")
  role_name               = "usmg-${var.env}-datamart-${local.fullname}-role"
  sg_name                 = coalesce(var.glue_security_group_name, "usmg-${var.env}-datamart-${local.fullname}-sg")
  artifact_bucket_name      = "usmg-${var.env}-datamart-artifact-bucket"
  script_bucket_name_default = coalesce(var.script_bucket_name, local.artifact_bucket_name)
  script_object_key          = coalesce(var.script_s3_key, "glue/scripts/job.py")
  should_upload_script       = var.local_script_path != null && fileexists("${path.module}/${var.local_script_path}")
  script_location_default    = "s3://${local.script_bucket_name_default}/${local.script_object_key}"
  script_location_effective  = local.should_upload_script ? local.script_location_default : coalesce(var.script_location, local.script_location_default)

  vpc_id               = data.terraform_remote_state.vpc.outputs.id
  non_routable_subnets = flatten(values(data.terraform_remote_state.vpc.outputs.subnets_non_routable_by_az))
  selected_subnet_id   = coalesce(var.glue_connection_subnet_id, try(local.non_routable_subnets[0].id, null))
  internal_egress_cidrs_effective = length(var.internal_egress_cidrs) > 0 ? var.internal_egress_cidrs : [data.aws_vpc.datamart_vpc.cidr_block]

  tags = merge(
    var.required_tags,
    var.optional_tags,
    var.data_at_rest_tags,
    {
      Application = var.app
      Environment = var.env
      Module      = local.fullname
    }
  )

  temp_dir_effective   = coalesce(var.temp_dir, "s3://${local.artifact_bucket_name}/glue/temp/")

  script_uri_no_scheme = local.script_location_effective != null ? replace(local.script_location_effective, "s3://", "") : null
  script_bucket_name_effective = local.script_uri_no_scheme != null ? split("/", local.script_uri_no_scheme)[0] : null
  script_key_effective         = local.script_uri_no_scheme != null ? join("/", slice(split("/", local.script_uri_no_scheme), 1, length(split("/", local.script_uri_no_scheme)))) : null
  script_bucket_arn = local.script_bucket_name_effective != null ? "arn:aws:s3:::${local.script_bucket_name_effective}" : null
  script_object_arn = local.script_bucket_name_effective != null && local.script_key_effective != null ? "arn:aws:s3:::${local.script_bucket_name_effective}/${local.script_key_effective}" : null
  temp_bucket_name  = split("/", replace(local.temp_dir_effective, "s3://", ""))[0]
  temp_bucket_arn   = "arn:aws:s3:::${local.temp_bucket_name}"
  temp_object_arn   = "${local.temp_bucket_arn}/*"

  target_bucket_prefixes_normalized = length(var.cross_account_bucket_prefixes) > 0 ? [for p in var.cross_account_bucket_prefixes : trim(p, "/")] : []
  target_object_arns = length(local.target_bucket_prefixes_normalized) > 0 ? [for p in local.target_bucket_prefixes_normalized : "arn:aws:s3:::${var.cross_account_bucket_name}/${p}/*"] : ["arn:aws:s3:::${var.cross_account_bucket_name}/*"]
  target_list_prefixes = length(local.target_bucket_prefixes_normalized) > 0 ? concat(local.target_bucket_prefixes_normalized, [for p in local.target_bucket_prefixes_normalized : "${p}/*"]) : ["*"]

  target_bucket_actions = concat(
    ["s3:ListBucket", "s3:GetBucketLocation"],
    contains(["write", "readwrite"], var.cross_account_access_mode) ? ["s3:ListBucketMultipartUploads"] : []
  )

  target_object_actions = concat(
    contains(["read", "readwrite"], var.cross_account_access_mode) ? ["s3:GetObject", "s3:GetObjectVersion"] : [],
    contains(["write", "readwrite"], var.cross_account_access_mode) ? ["s3:PutObject", "s3:AbortMultipartUpload"] : [],
    var.allow_delete_in_target_prefixes ? ["s3:DeleteObject", "s3:DeleteObjectVersion"] : []
  )

  connection_properties_effective = upper(var.glue_connection_type) == "NETWORK" ? {} : merge(
    var.connection_properties,
    var.secret_arn_for_connection != null ? { SECRET_ID = var.secret_arn_for_connection } : {}
  )

  base_default_arguments = merge(
    {
      "--TempDir"            = local.temp_dir_effective
      "--job-bookmark-option" = var.job_bookmark_option
    },
    var.enable_glue_datacatalog ? { "--enable-glue-datacatalog" = "true" } : {},
    var.enable_continuous_logging ? { "--enable-continuous-cloudwatch-log" = "true" } : {},
    var.enable_metrics ? { "--enable-metrics" = "true" } : {},
    var.enable_spark_ui ? { "--enable-spark-ui" = "true" } : {},
    var.extra_python_files != null ? { "--extra-py-files" = var.extra_python_files } : {},
    var.extra_jars != null ? { "--extra-jars" = var.extra_jars } : {}
  )

  default_arguments_effective = merge(local.base_default_arguments, var.default_arguments)
  connection_names_effective  = concat([aws_glue_connection.this.name], var.connections)
}
