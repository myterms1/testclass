data "terraform_remote_state" "vpc" {
  backend = "s3"
  config = {
    bucket = var.tf_state_bucket
    key    = var.vpc_state_file
    region = var.awsRegion
  }
}

data "aws_vpc" "datamart_vpc" {
  id = local.vpc_id
}

data "aws_subnet" "glue_connection" {
  id = local.selected_subnet_id
}

resource "aws_s3_object" "glue_script" {
  count  = local.should_upload_script ? 1 : 0
  bucket = local.script_bucket_name_default
  key    = local.script_object_key
  source = "${path.module}/${var.local_script_path}"
  etag   = filemd5("${path.module}/${var.local_script_path}")

  tags = local.tags
}
