I've written two Python scripts, one to check and snapshot the volumes and one to delete them later. I tested them against a simulated AWS account, not your real accounts, so the dry run in usmg-dev will be their first real test.

**What's in the FinOps file:** 82 rows, all in us-east-1. 81 are EBS volumes: 17 in usmg-dev (851725216779), 27 in usmg-test (084828583690) and 37 in usmg-prod (971422678837). I pulled these into `volumes.csv`, which both scripts read.

**`snapshot_unused_volumes.py`** — run it with `--account usmg-dev`. For each volume it:
- checks that the volume still exists and whether it's attached to any instance, including stopped ones;
- creates a snapshot only if the volume is not attached;
- skips attached volumes and records which instance each one is attached to;
- keeps the volume's tags on the snapshot and adds a few, such as `SourceVolumeId` and `CreatedBy`.

**`delete_snapshotted_volumes.py`** reads the report from the snapshot run. Just before deleting each volume it checks again that its snapshot is `completed` and that the volume is still not attached. If either check fails, it skips that volume.

**Safety checks in both scripts:**
- **Dry run by default:** nothing changes unless you add `--execute`, and the dry run also checks your AWS permissions.
- **Account check:** a script stops if your credentials belong to a different account than the one you named.
- **Confirmation before deleting:** the delete script asks you to type the account name.
- **Safe to re-run:** running the snapshot script again reuses snapshots it already made instead of creating duplicates.
- **Reports:** every run writes a CSV report.

The exact commands for dev, then test and prod, are in `README.md`.

Two things to know before you run them:
- **13 volumes will be skipped** (dev 4, test 4, prod 5). FinOps marked these "Detach volume from instance…", so they're attached to an instance, probably a stopped one. Following your rule, the script won't snapshot them. They'll show as `IN_USE_SKIPPED` in the report with the instance ID, so you can decide about them separately.
- **Most of these volumes were created by Kubernetes for EKS clusters.** Their Kubernetes records may still exist after the AWS volume is deleted. Before running the delete script in each account, check whether anything in the cluster still points at each volume (for example `kubectl get pv | grep <vol-id>`). Otherwise a pod that later needs that storage will fail to start.