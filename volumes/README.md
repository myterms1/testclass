# FinOps unused EBS volume cleanup (usmg-dev / usmg-test / usmg-prod)

Files
- `volumes.csv`: 81 EBS volumes from the FinOps sheet (dev 17, test 27, prod 37), all us-east-1
- `snapshot_unused_volumes.py`: Step 1. Checks for attachments; snapshots only the unattached volumes
- `delete_snapshotted_volumes.py`: Step 2. Deletes only volumes whose snapshot is `completed` and which are still unattached

Requirements: Python 3 + boto3 (already in AWS CloudShell), and credentials for the target account.
IAM actions needed: `sts:GetCallerIdentity`, `ec2:DescribeVolumes`, `ec2:DescribeInstances`,
`ec2:DescribeSnapshots`, `ec2:CreateSnapshot`, `ec2:CreateTags`, `ec2:DeleteVolume`.

## Run in usmg-dev first

```bash
# 1. Dry run: no changes; also confirms your IAM permissions
python3 snapshot_unused_volumes.py --account usmg-dev [--profile <dev-profile>]

# 2. Review snapshot_report_usmg-dev_*_DRYRUN.csv, then create the snapshots
python3 snapshot_unused_volumes.py --account usmg-dev --execute --wait

# 3. Later: delete the volumes (dry run first, then for real)
python3 delete_snapshotted_volumes.py --account usmg-dev --report snapshot_report_usmg-dev_<ts>.csv
python3 delete_snapshotted_volumes.py --account usmg-dev --report snapshot_report_usmg-dev_<ts>.csv --execute
```

Repeat the same steps with `--account usmg-test`, then `--account usmg-prod`.

## Safety built in
- Stops if your credentials belong to a different account than the one in `--account`.
- Dry run is the default. Real changes need `--execute`, and deleting also asks you to type the account name.
- Attached volumes, including those attached to stopped instances, are never snapshotted or deleted (status `IN_USE_SKIPPED`).
- Re-running step 1 is safe: it reuses snapshots made by an earlier run instead of creating duplicates.
- Step 2 re-checks every volume right before deleting it. A volume that was attached after the snapshot was taken is skipped.
- Snapshots keep the volume's business tags and add `SourceVolumeId`, `CreatedBy=ebs-finops-cleanup` and `CleanupDate`.
  Kubernetes/CSI tags are not copied.
- Every run writes a CSV report.

## Restore a volume
```bash
aws ec2 create-volume --snapshot-id snap-xxxx --availability-zone us-east-1a --volume-type gp3
```
Use the AZ and volume type from the snapshot's `SourceAvailabilityZone` and `SourceVolumeType` tags.
