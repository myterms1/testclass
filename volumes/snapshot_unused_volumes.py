#!/usr/bin/env python3
"""
Step 1 of the FinOps EBS cleanup.

For every volume listed in volumes.csv for ONE account:
  * checks whether the volume still exists
  * checks whether it is attached to any EC2 instance (running OR stopped)
  * if it is NOT attached (state = available) -> creates a snapshot
  * if it IS attached -> skips it and records which instance it is attached to

Nothing is deleted by this script.

Default mode is DRY RUN (no snapshots are created, AWS permissions are still
checked with EC2 DryRun calls). Add --execute to really create snapshots.

Examples
  python3 snapshot_unused_volumes.py --account usmg-dev                    # dry run
  python3 snapshot_unused_volumes.py --account usmg-dev --execute --wait   # real run
  python3 snapshot_unused_volumes.py --account usmg-dev --profile usmg-dev --execute --wait

Output: snapshot_report_<account>_<timestamp>.csv  (this file is the input of
delete_snapshotted_volumes.py)
"""
import argparse
import csv
import datetime as dt
import sys
import time
from collections import defaultdict

import boto3
from botocore.exceptions import ClientError

TOOL_TAG = "ebs-finops-cleanup"
# Tags we do NOT copy from volume to snapshot (reserved, or used by Kubernetes / EBS CSI driver)
SKIP_TAG_PREFIXES = ("aws:", "kubernetes.io/", "ebs.csi.aws.com/")

REPORT_FIELDS = [
    "account_name", "account_id", "region", "volume_id", "volume_name", "k8s_cluster",
    "size_gib", "volume_type", "volume_state", "attached_instances", "instance_states",
    "status", "snapshot_id", "snapshot_state", "message",
]


def log(msg):
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


def is_dry_run_ok(err):
    return isinstance(err, ClientError) and err.response["Error"]["Code"] == "DryRunOperation"


def load_volumes(path, account):
    with open(path, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["account_name"] == account]
    if not rows:
        sys.exit(f"No volumes found for account '{account}' in {path}")
    ids = {r["account_id"] for r in rows}
    if len(ids) != 1:
        sys.exit(f"More than one account id for {account} in {path}: {ids}")
    return rows, ids.pop()


def find_existing_snapshot(ec2, volume_id):
    """Return a snapshot this tool already made for the volume (makes re-runs safe)."""
    resp = ec2.describe_snapshots(
        OwnerIds=["self"],
        Filters=[
            {"Name": "volume-id", "Values": [volume_id]},
            {"Name": "tag:CreatedBy", "Values": [TOOL_TAG]},
        ],
    )
    snaps = [s for s in resp["Snapshots"] if s["State"] in ("pending", "completed")]
    snaps.sort(key=lambda s: s["StartTime"], reverse=True)
    return snaps[0] if snaps else None


def instance_states(ec2, instance_ids):
    if not instance_ids:
        return {}
    try:
        resp = ec2.describe_instances(InstanceIds=instance_ids)
        return {
            i["InstanceId"]: i["State"]["Name"]
            for r in resp["Reservations"] for i in r["Instances"]
        }
    except ClientError as e:
        return {iid: f"unknown ({e.response['Error']['Code']})" for iid in instance_ids}


def snapshot_tags(volume, today):
    tags = [
        t for t in volume.get("Tags", [])
        if not t["Key"].startswith(SKIP_TAG_PREFIXES)
    ]
    tags += [
        {"Key": "CreatedBy", "Value": TOOL_TAG},
        {"Key": "SourceVolumeId", "Value": volume["VolumeId"]},
        {"Key": "SourceVolumeSizeGiB", "Value": str(volume["Size"])},
        {"Key": "SourceVolumeType", "Value": volume["VolumeType"]},
        {"Key": "SourceAvailabilityZone", "Value": volume["AvailabilityZone"]},
        {"Key": "CleanupDate", "Value": today},
        {"Key": "CleanupReason", "Value": "FinOps ComputeOptimizer - unused EBS volume"},
    ]
    # tag keys must be unique
    seen, uniq = set(), []
    for t in tags:
        if t["Key"] not in seen:
            seen.add(t["Key"])
            uniq.append(t)
    return uniq[:50]  # AWS limit: 50 tags per resource


def process_volume(ec2, row, execute, today):
    out = {k: "" for k in REPORT_FIELDS}
    out.update({k: row[k] for k in ("account_name", "account_id", "region", "volume_id",
                                     "volume_name", "k8s_cluster")})
    vid = row["volume_id"]

    try:
        vol = ec2.describe_volumes(VolumeIds=[vid])["Volumes"][0]
    except ClientError as e:
        if e.response["Error"]["Code"] == "InvalidVolume.NotFound":
            out.update(status="NOT_FOUND", message="Volume no longer exists - nothing to do")
        else:
            out.update(status="ERROR", message=str(e))
        return out

    attachments = vol.get("Attachments", [])
    inst_ids = [a["InstanceId"] for a in attachments]
    states = instance_states(ec2, inst_ids)
    out.update(
        size_gib=vol["Size"],
        volume_type=vol["VolumeType"],
        volume_state=vol["State"],
        attached_instances=";".join(inst_ids),
        instance_states=";".join(f"{i}={states.get(i, '')}" for i in inst_ids),
    )

    if attachments or vol["State"] != "available":
        out.update(status="IN_USE_SKIPPED",
                   message="Volume is attached to an instance (or not in 'available' state) - not touched")
        return out

    existing = find_existing_snapshot(ec2, vid)
    if existing:
        out.update(status="SNAPSHOT_ALREADY_EXISTS", snapshot_id=existing["SnapshotId"],
                   snapshot_state=existing["State"],
                   message="Snapshot created by an earlier run of this script - reused")
        return out

    params = dict(
        VolumeId=vid,
        Description=f"Pre-delete backup of {vid} ({row['volume_name']}) - FinOps cleanup {today}"[:255],
        TagSpecifications=[{"ResourceType": "snapshot", "Tags": snapshot_tags(vol, today)}],
    )

    if not execute:
        try:
            ec2.create_snapshot(DryRun=True, **params)
            out.update(status="WOULD_SNAPSHOT", message="Dry run OK (permissions verified)")
        except ClientError as e:
            if is_dry_run_ok(e):
                out.update(status="WOULD_SNAPSHOT", message="Dry run OK (permissions verified)")
            else:
                out.update(status="ERROR", message=f"Dry run failed: {e}")
        return out

    try:
        snap = ec2.create_snapshot(**params)
        out.update(status="SNAPSHOT_CREATED", snapshot_id=snap["SnapshotId"],
                   snapshot_state=snap["State"])
    except ClientError as e:
        out.update(status="ERROR", message=str(e))
    return out


def wait_for_snapshots(clients, results, timeout_min):
    pending = defaultdict(list)
    for r in results:
        if r["snapshot_id"] and r["snapshot_state"] != "completed":
            pending[r["region"]].append(r)
    if not pending:
        return
    log(f"Waiting up to {timeout_min} min for {sum(len(v) for v in pending.values())} snapshot(s) to complete...")
    deadline = time.time() + timeout_min * 60
    while pending and time.time() < deadline:
        for region in list(pending):
            rows = pending[region]
            by_id = {r["snapshot_id"]: r for r in rows}
            ids = list(by_id)
            for i in range(0, len(ids), 100):
                resp = clients[region].describe_snapshots(SnapshotIds=ids[i:i + 100])
                for s in resp["Snapshots"]:
                    r = by_id[s["SnapshotId"]]
                    r["snapshot_state"] = s["State"]
                    if s["State"] == "error":
                        r["status"] = "ERROR"
                        r["message"] = f"Snapshot failed: {s.get('StateMessage', '')}"
            pending[region] = [r for r in rows if r["snapshot_state"] == "pending"]
            if not pending[region]:
                del pending[region]
        if pending:
            left = sum(len(v) for v in pending.values())
            log(f"  {left} snapshot(s) still pending...")
            time.sleep(30)
    if pending:
        log("Timeout reached - some snapshots are still pending. That is OK: the delete "
            "script re-checks every snapshot and only deletes when it is 'completed'.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--account", required=True, choices=["usmg-dev", "usmg-test", "usmg-prod"])
    p.add_argument("--input", default="volumes.csv")
    p.add_argument("--profile", help="AWS CLI profile to use (optional)")
    p.add_argument("--execute", action="store_true", help="Really create snapshots (default: dry run)")
    p.add_argument("--wait", action="store_true", help="Wait until snapshots are completed")
    p.add_argument("--wait-minutes", type=int, default=60)
    args = p.parse_args()

    rows, expected_account = load_volumes(args.input, args.account)
    session = boto3.Session(profile_name=args.profile) if args.profile else boto3.Session()

    # Safety: make sure the credentials belong to the account we were asked to work on
    actual = session.client("sts").get_caller_identity()["Account"]
    if actual != expected_account:
        sys.exit(f"ABORT: credentials are for account {actual}, but {args.account} is {expected_account}")

    mode = "EXECUTE" if args.execute else "DRY RUN"
    log(f"Account {args.account} ({actual}) - {len(rows)} volume(s) - mode: {mode}")

    today = dt.date.today().isoformat()
    clients, results = {}, []
    for n, row in enumerate(rows, 1):
        region = row["region"]
        if region not in clients:
            clients[region] = session.client("ec2", region_name=region)
        r = process_volume(clients[region], row, args.execute, today)
        results.append(r)
        extra = r["snapshot_id"] or r["attached_instances"] or ""
        log(f"[{n}/{len(rows)}] {r['volume_id']:<22} {r['status']:<24} {extra}")

    if args.execute and args.wait:
        wait_for_snapshots(clients, results, args.wait_minutes)

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "" if args.execute else "_DRYRUN"
    report = f"snapshot_report_{args.account}_{ts}{suffix}.csv"
    with open(report, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REPORT_FIELDS)
        w.writeheader()
        w.writerows(results)

    counts = defaultdict(int)
    for r in results:
        counts[r["status"]] += 1
    log("Summary:")
    for k, v in sorted(counts.items()):
        log(f"  {k:<26} {v}")
    log(f"Report written: {report}")
    if counts.get("ERROR"):
        sys.exit(1)


if __name__ == "__main__":
    main()
