{
  "Version": "2012-10-17",
  "Statement": [

    ### ✅ Lambda: Allow viewing status only
    {
      "Effect": "Allow",
      "Action": [
        "lambda:GetFunctionConfiguration"
      ],
      "Resource": "arn:aws:lambda:*:*:function:vvv-claim-intake-path-determiner-dev"
    },

    ### ❌ Lambda/CloudWatch: Deny access to logs to protect PHI
    {
      "Effect": "Deny",
      "Action": [
        "logs:GetLogEvents",
        "logs:DescribeLogStreams",
        "logs:DescribeLogGroups",
        "logs:FilterLogEvents"
      ],
      "Resource": "*"
    },

    ### ✅ SQS: Read-only access to one queue
    {
      "Effect": "Allow",
      "Action": [
        "sqs:GetQueueAttributes",
        "sqs:GetQueueUrl",
        "sqs:ReceiveMessage"
      ],
      "Resource": "arn:aws:sqs:*:*:vvv-dev-pathDeterminer-queue"
    },

    ### ✅ S3: List and object metadata (no content)
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetObjectAttributes",
        "s3:GetObjectTagging",
        "s3:GetObjectAcl"
      ],
      "Resource": [
        "arn:aws:s3:::vvv-dev-claims-replay-letter",
        "arn:aws:s3:::vvv-dev-claims-replay-letter/*",
        "arn:aws:s3:::vvv-dev-path-determiner-trigger-bucket",
        "arn:aws:s3:::vvv-dev-path-determiner-trigger-bucket/*"
      ]
    },

    ### ✅ S3: Move (copy + delete) files within same bucket
    {
      "Effect": "Allow",
      "Action": [
        "s3:CopyObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::vvv-dev-claims-replay-letter/*",
        "arn:aws:s3:::vvv-dev-path-determiner-trigger-bucket/*"
      ]
    },

    ### ✅ S3: Allow uploading of only `.csv` files anywhere
    {
      "Effect": "Allow",
      "Action": "s3:PutObject",
      "Resource": [
        "arn:aws:s3:::vvv-dev-claims-replay-letter/*",
        "arn:aws:s3:::vvv-dev-path-determiner-trigger-bucket/*"
      ],
      "Condition": {
        "StringLike": {
          "s3:Key": "*.csv"
        }
      }
    },

    ### ❌ S3: Deny downloading files
    {
      "Effect": "Deny",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:GetObjectTorrent"
      ],
      "Resource": "*"
    },

    ### ✅ CloudWatch: Allow metric access for specific namespaces
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricData",
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "cloudwatch:namespace": [
            "AWS/Glue",
            "AWS/States",
            "AWS/Lambda"
          ]
        }
      }
    }

  ]
}
