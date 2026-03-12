data "aws_iam_policy_document" "target_bucket_policy" {
  statement {
    sid    = "AllowGlueRoleBucketAccess"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.glue.arn]
    }

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
    sid    = "AllowGlueRoleObjectAccess"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.glue.arn]
    }

    actions   = local.target_object_actions
    resources = local.target_object_arns
  }
}

data "aws_iam_policy_document" "target_kms_policy" {
  statement {
    sid    = "AllowGlueRoleKmsUsage"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.glue.arn]
    }

    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
      "kms:Encrypt",
      "kms:GenerateDataKey",
      "kms:GenerateDataKeyWithoutPlaintext",
      "kms:ReEncryptFrom",
      "kms:ReEncryptTo"
    ]

    resources = ["*"]
  }
}
