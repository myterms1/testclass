####################################################################################################################################
variables.tf

variable "config" {
  type = object({
    name      = string
    env       = string
    tags      = map(string)
    data_tags = map(string)
    caller = object({
      account_id  = string
      account_env = string
      region      = string
    })
    vpc = object({
      id = string
      subnets = object({
        nonroutable = list(string)
      })
    })
    remotes = object({
      cmn_base    = any
      cmn_buckets = any
      cmn_db      = any
    })
    assume_role = object({
      ec2 = string
    })
  })
}

variable "bastion" {
  type = object({
    tag           = string
    ami           = string
    instance_type = optional(string, "t3.micro")
    userdata      = optional(string)
  })
}

variable "golden_ami_encryption_key_id" {
  type        = string
  description = "KMS key for decrypting EC2 AMI and its volumes"
}

####################################################################################################################################
_datasources.tf:

data "aws_region" "current" {}

module "config" {
  source      = "../../_modules/config"
  app         = "commons"
  name_suffix = "bastion"
  env         = var.env
  remotes = {
    cmn_base    = "usmg-state/${data.aws_region.current.name}/companyxyz/commons/base/${var.env}-tfstate"
    cmn_buckets = "usmg-state/${data.aws_region.current.name}/companyxyz/commons/buckets/${var.env}-tfstate"
    cmn_db      = "usmg-state/${data.aws_region.current.name}/companyxyz/commons/db/${var.env}-tfstate"
  }
  gen_assume_role = ["ec2"]
}

data "aws_ram_resource_share" "ami_params_linux" {
  resource_owner = "OTHER-ACCOUNTS"
  name           = "zilverton-golden-ami-cis-linux-dev"
}

data "aws_ssm_parameter" "linux_ami" {
  name = [
    for resource in data.aws_ram_resource_share.ami_params_linux.resource_arns : resource
    if endswith(resource, "/dev/golden-cis-linux")
  ][0]
}

variable "env" {
  type = string
}

locals {
  kms_key_map = {
    "dev"  = "arn:aws:kms:us-east-1:447355:key/mrk-a47f0"
    "int"  = "arn:aws:kms:us-east-1:3823:key/mrk-b021fc"
    "prod" = "arn:aws:kms:us-east-1:3823:key/mrk-b021fc"
  }
}
####################################################################################################################################
bastion.tf:
resource "aws_launch_template" "bastion" {
  name_prefix   = "${var.config.name}-"
  image_id      = var.bastion.ami
  instance_type = var.bastion.instance_type
  user_data     = var.bastion.userdata
  vpc_security_group_ids = [
    var.config.remotes.cmn_base.sgs.aurora_connect,
    var.config.remotes.cmn_base.sgs.internet_egress,
  ]

  iam_instance_profile {
    arn = aws_iam_instance_profile.bastion.arn
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "enabled"
  }

  tag_specifications {
    resource_type = "volume"
    tags          = merge({ Name = var.config.name, Bastion = var.bastion.tag }, merge(var.config.tags, var.config.data_tags))
  }

  tag_specifications {
    resource_type = "instance"
    tags          = merge({ Name = var.config.name, Bastion = var.bastion.tag }, var.config.tags)
  }
}

resource "aws_autoscaling_group" "bastion" {
  name                = var.config.name
  vpc_zone_identifier = var.config.vpc.subnets.nonroutable
  desired_capacity    = 1
  max_size            = 1
  min_size            = 1
  health_check_type   = "EC2"

  launch_template {
    id      = aws_launch_template.bastion.id
    version = aws_launch_template.bastion.latest_version
  }

  instance_refresh {
    strategy = "Rolling"
    preferences {
      auto_rollback = true
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_kms_grant" "golden-ami" {
  name              = "${var.config.name}-${var.config.env}-ec2-golden-ami"
  key_id            = var.golden_ami_encryption_key_id
  grantee_principal = "arn:aws:iam::${var.config.caller.account_id}:role/aws-service-role/autoscaling.amazonaws.com/AWSServiceRoleForAutoScaling"
  
  operations = [
    "Encrypt",
    "Decrypt",
    "ReEncryptFrom",
    "ReEncryptTo",
    "GenerateDataKey",
    "GenerateDataKeyWithoutPlaintext",
    "DescribeKey",
    "CreateGrant"
  ]
  retire_on_delete = false
}

####################################################################################################################################
main.tf:

module "bastion" {
  source = "../../_modules/bastion"
  config = module.config
  bastion = {
    tag = "Main"
    ami = data.aws_ssm_parameter.linux_ami.value
  }
  golden_ami_encryption_key_id = lookup(local.kms_key_map, var.env, local.kms_key_map["prod"])
}
####################################################################################################################################
####################################################################################################################################
####################################################################################################################################
####################################################################################################################################
####################################################################################################################################
####################################################################################################################################
####################################################################################################################################


///////////////////////////////////////////
variable "golden_ami_encryption_key_id" {
  type = string
  description = "KMS key for decrypting the EC2 AMI and its volume"
}

resource "aws_kms_grant" "golden-ami" {
  name              = "${var.config.name}-${var.config.env}-ec2-golden-ami"
  key_id            = var.golden_ami_encryption_key_id
  grantee_principal = "arn:aws:iam::${var.config.caller.account_id}:role/aws-service-role/autoscaling.amazonaws.com/AWSServiceRoleForAutoScaling"
  
  operations = [
    "Encrypt",
    "Decrypt",
    "ReEncryptFrom",
    "ReEncryptTo",
    "GenerateDataKey",
    "GenerateDataKeyWithoutPlaintext",
    "DescribeKey",
    "CreateGrant"
  ]
  retire_on_delete = false
}


locals {
  kms_key_map = {
    "dev"  = "arn:aws:kms:us-east-1:0582644:key/mrk-0f7142"
    "int"  = "arn:aws:kms:us-east-1:3823581:key/mrk-bcb1"
    "prod" = "arn:aws:kms:us-east-1:382358:key/mrk-b5bc"
  }
}

module "bastion" {
  source = "../../_modules/bastion"
  config = module.config
  bastion = {
    tag = "Main"
    ami = data.aws_ssm_parameter.linux_ami.value
  }
  golden_ami_encryption_key_id = lookup(local.kms_key_map, var.env, local.kms_key_map["prod"]) 
}




