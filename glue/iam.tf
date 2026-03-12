data "aws_iam_policy_document" "glue_assume_role" {
  statement {
    effect = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "glue" {
  name               = local.role_name
  assume_role_policy = data.aws_iam_policy_document.glue_assume_role.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "aws_glue_service_role" {
  role       = aws_iam_role.glue.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

data "aws_iam_policy_document" "glue_inline" {
  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:AssociateKmsKey"
    ]
    resources = ["*"]
  }

  statement {
    sid    = "VpcNetworking"
    effect = "Allow"
    actions = [
      "ec2:CreateNetworkInterface",
      "ec2:DeleteNetworkInterface",
      "ec2:DescribeAvailabilityZones",
      "ec2:DescribeNetworkInterfaces",
      "ec2:DescribeRouteTables",
      "ec2:DescribeSecurityGroups",
      "ec2:DescribeSubnets",
      "ec2:DescribeVpcEndpoints",
      "ec2:DescribeVpcs"
    ]
    resources = ["*"]
  }

  statement {
    sid    = "GlueScriptBucketRead"
    effect = "Allow"
    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket"
    ]
    resources = compact([local.script_bucket_arn, local.temp_bucket_arn])
  }

  statement {
    sid    = "GlueScriptObjectReadWrite"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:PutObject",
      "s3:AbortMultipartUpload"
    ]
    resources = compact([local.script_object_arn, local.temp_object_arn])
  }

  statement {
    sid       = "CrossAccountBucketAccess"
    effect    = "Allow"
    actions   = local.target_bucket_actions
    resources = ["arn:aws:s3:::${var.cross_account_bucket_name}"]

    dynamic "condition" {
      for_each = length(local.target_bucket_prefixes_normalized) > 0 ? [1] : []
      content {
        test     = "StringLike"
        variable = "s3:prefix"
        values   = local.target_list_prefixes
      }
    }
  }

  statement {
    sid       = "CrossAccountObjectAccess"
    effect    = "Allow"
    actions   = local.target_object_actions
    resources = local.target_object_arns
  }

  dynamic "statement" {
    for_each = length(var.secret_arns) > 0 ? [1] : []
    content {
      sid     = "SecretsManagerRead"
      effect  = "Allow"
      actions = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
      resources = var.secret_arns
    }
  }

  dynamic "statement" {
    for_each = length(var.kms_key_arns) > 0 ? [1] : []
    content {
      sid    = "KmsUsage"
      effect = "Allow"
      actions = [
        "kms:Decrypt",
        "kms:DescribeKey",
        "kms:Encrypt",
        "kms:GenerateDataKey",
        "kms:GenerateDataKeyWithoutPlaintext",
        "kms:ReEncryptFrom",
        "kms:ReEncryptTo"
      ]
      resources = var.kms_key_arns

      dynamic "condition" {
        for_each = var.kms_via_service_s3_only ? [1] : []
        content {
          test     = "StringEquals"
          variable = "kms:ViaService"
          values   = ["s3.${var.awsRegion}.amazonaws.com"]
        }
      }
    }
  }
}

resource "aws_iam_policy" "glue_inline" {
  name   = "${local.role_name}-perms"
  policy = data.aws_iam_policy_document.glue_inline.json
}

resource "aws_iam_role_policy_attachment" "glue_inline" {
  role       = aws_iam_role.glue.name
  policy_arn = aws_iam_policy.glue_inline.arn
}

resource "aws_iam_role_policy" "additional" {
  count  = var.additional_policy_json != null ? 1 : 0
  name   = "${local.role_name}-additional"
  role   = aws_iam_role.glue.id
  policy = var.additional_policy_json
}
