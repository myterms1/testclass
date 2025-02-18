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
    "dev"  = "arn:aws:kms:us-east-1:0582644:key/mrk-0f71429b9527a8"
    "int"  = "arn:aws:kms:us-east-1:3823581:key/mrk-bcb1474c82a9"
    "prod" = "arn:aws:kms:us-east-1:382358:key/mrk-b5bcb1474c82a9"
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




