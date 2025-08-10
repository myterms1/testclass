statements:

  # --- Keep: EventBridge/Scheduler list-only (from your screenshot) ---
  - effect: "Allow"
    actions:
      - events:ListRules
      - events:DescribeRule
      - events:ListEventBuses
      - events:ListTargetsByRule
      - scheduler:ListSchedules
      - scheduler:GetSchedule
    resources:
      - "*"

  # --- Lambda: status only, no logs ---
  - effect: "Allow"
    actions:
      - lambda:GetFunctionConfiguration
    resources:
      - !Sub "arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:gbs-claim-intake-path-determiner-pre3"

  - effect: "Deny"
    actions:
      - logs:GetLogEvents
      - logs:DescribeLogStreams
      - logs:DescribeLogGroups
      - logs:FilterLogEvents
    resources:
      - "*"

  # --- SQS: read-only to the specific queue ---
  - effect: "Allow"
    actions:
      - sqs:GetQueueAttributes
      - sqs:GetQueueUrl
      - sqs:ReceiveMessage
    resources:
      - !Sub "arn:aws:sqs:${AWS::Region}:${AWS::AccountId}:gbs-pre3-pathDeterminer-queue"

  # --- S3: bucket-level listing (limit to the two buckets) ---
  - effect: "Allow"
    actions:
      - s3:ListBucket
      - s3:GetBucketLocation
    resources:
      - "arn:aws:s3:::gbs-pre3-claims-replay-letter"
      - "arn:aws:s3:::gbs-pre3-path-determiner-trigger-bucket"

  # --- S3: object metadata view (no content download) across required folders ---
  - effect: "Allow"
    actions:
      - s3:GetObjectAttributes
      - s3:GetObjectTagging
      - s3:GetObjectAcl
    resources:
      - "arn:aws:s3:::gbs-pre3-claims-replay-letter/*"
      - "arn:aws:s3:::gbs-pre3-path-determiner-trigger-bucket/*"

  # --- S3: allow moving files (copy + delete) within the same bucket ---
  - effect: "Allow"
    actions:
      - s3:CopyObject
      - s3:DeleteObject
    resources:
      - "arn:aws:s3:::gbs-pre3-claims-replay-letter/*"
      - "arn:aws:s3:::gbs-pre3-path-determiner-trigger-bucket/*"

  # --- S3: allow uploading ONLY .csv files anywhere in the buckets ---
  - effect: "Allow"
    actions:
      - s3:PutObject
    resources:
      - "arn:aws:s3:::gbs-pre3-claims-replay-letter/*"
      - "arn:aws:s3:::gbs-pre3-path-determiner-trigger-bucket/*"
    condition:
      StringLike:
        s3:Key: "*.csv"

  # --- S3: explicitly deny downloads from anywhere (protect PHI) ---
  - effect: "Deny"
    actions:
      - s3:GetObject
      - s3:GetObjectVersion
      - s3:GetObjectTorrent
    resources:
      - "*"

  # --- (Optional but useful) S3: block cross-account write/delete/copy ---
  #     Keeps actions in-account; explicit Deny wins over Allows above only
  #     when the bucket is not owned by this account.
  - effect: "Deny"
    actions:
      - s3:PutObject
      - s3:DeleteObject
      - s3:CopyObject
    resources:
      - "arn:aws:s3:::gbs-*/*"
    condition:
      StringNotEquals:
        s3:ResourceAccount:
          - !Sub "${AWS::AccountId}"

  # --- CloudWatch: metrics-only (best-possible precision) ---
  # NOTE: CloudWatch metric APIs can't be scoped to specific resource names.
  # We allow metrics for AWS/Glue, AWS/States, AWS/Lambda namespaces.
  - effect: "Allow"
    actions:
      - cloudwatch:GetMetricData
      - cloudwatch:GetMetricStatistics
      - cloudwatch:ListMetrics
    resources:
      - "*"

  # --- Keep/augment your existing Glue read permissions (no run) ---
  - effect: "Allow"
    actions:
      - glue:ListJobs
      - glue:GetJobs
    resources:
      - "*"

  - effect: "Allow"
    actions:
      - glue:GetJobs
      - glue:GetJob
      - glue:ListJobs
      - glue:GetJobRuns
      - glue:GetJobRun
      - glue:GetJobBookmark
      - glue:BatchGetJobs
      - glue:GetWorkflow
      - glue:GetWorkflowRun
      - glue:GetWorkflowRuns
      - glue:GetWorkflowProperties
      - glue:GetTags
      - glue:GetDataCatalogEncryptionSettings
    resources:
      - !Sub "arn:aws:glue:${AWS::Region}:${AWS::AccountId}:job/gbs-*"
      - !Sub "arn:aws:glue:${AWS::Region}:${AWS::AccountId}:workflow/gbs-*"

  # --- Keep: Step Functions read-only (list/describe) ---
  - effect: "Allow"
    actions:
      - states:ListStateMachines
    resources:
      - "*"

  - effect: "Allow"
    actions:
      - states:DescribeExecution
      - states:ListExecutions
      - states:DescribeStateMachines
      - states:DescribeStateMachine
      - states:GetExecutionHistory
    resources:
      - !Sub "arn:aws:states:${AWS::Region}:${AWS::AccountId}:stateMachine:gbs-*"
      - !Sub "arn:aws:states:${AWS::Region}:${AWS::AccountId}:execution:gbs-*"