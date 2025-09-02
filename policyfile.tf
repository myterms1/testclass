variable "bucket" {
  description = "S3 bucket name"
  type        = string
}

variable "account_id" {
  description = "AWS Account ID"
  type        = string
}

data "aws_iam_policy_document" "s3_bucket_policy" {

  # --- Deny non-TLS requests ---
  statement {
    sid    = "AllowTLSRequestsOnly"
    effect = "Deny"

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    actions = ["s3:*"]

    resources = [
      "arn:aws:s3:::${var.bucket}",
      "arn:aws:s3:::${var.bucket}/*"
    ]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

  # --- Deny public read ACLs on objects ---
  statement {
    sid    = "DenyPublicReadACL"
    effect = "Deny"

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    actions   = ["s3:PutObject", "s3:PutObjectAcl"]
    resources = ["arn:aws:s3:::${var.bucket}/*"]

    condition {
      test     = "StringEquals"
      variable = "s3:x-amz-acl"
      values   = ["public-read", "public-read-write", "authenticated-read"]
    }
  }

  # --- Deny public grants on objects ---
  statement {
    sid    = "DenyPublicReadGrant"
    effect = "Deny"

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    actions   = ["s3:PutObject", "s3:PutObjectAcl"]
    resources = ["arn:aws:s3:::${var.bucket}/*"]

    condition {
      test     = "StringLike"
      variable = "s3:x-amz-grant-read"
      values   = [
        "http://acs.amazonaws.com/groups/global/AllUsers*",
        "http://acs.amazonaws.com/groups/global/AuthenticatedUsers*"
      ]
    }
  }

  # --- Deny public ACL on bucket ---
  statement {
    sid    = "DenyPublicListACL"
    effect = "Deny"

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    actions   = ["s3:PutBucketAcl"]
    resources = ["arn:aws:s3:::${var.bucket}"]

    condition {
      test     = "StringEquals"
      variable = "s3:x-amz-acl"
      values   = ["public-read", "public-read-write", "authenticated-read"]
    }
  }

  # --- Deny public grants on bucket ---
  statement {
    sid    = "DenyPublicListGrant"
    effect = "Deny"

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    actions   = ["s3:PutBucketAcl"]
    resources = ["arn:aws:s3:::${var.bucket}"]

    condition {
      test     = "StringLike"
      variable = "s3:x-amz-grant-read"
      values   = [
        "http://acs.amazonaws.com/groups/global/AllUsers*",
        "http://acs.amazonaws.com/groups/global/AuthenticatedUsers*"
      ]
    }
  }

  # --- Allow specific account/role ---
  statement {
    sid    = "Allow"
    effect = "Allow"

    principals {
      type = "AWS"
      identifiers = [
        "arn:aws:iam::${var.account_id}:role/Enterprise/UsmgDeployer",
        "arn:aws:iam::${var.account_id}:root"
      ]
    }

    actions = [
      "s3:Get*",
      "s3:List*",
      "s3:DeleteObject",
      "s3:PutObject"
    ]

    resources = [
      "arn:aws:s3:::${var.bucket}",
      "arn:aws:s3:::${var.bucket}/*"
    ]
  }
}