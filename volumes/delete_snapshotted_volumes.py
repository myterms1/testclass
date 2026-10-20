#!/usr/bin/env python3
"""
Step 2 of the FinOps EBS cleanup.

Reads the snapshot report produced by snapshot_unused_volumes.py and deletes a
volume ONLY when ALL of these are true at the moment of deletion:
  1. the report has a snapshot id for the volume
  2. that snapshot exists, is in state 'completed', and was taken from this volume
  3. the volume still exists, is in state 'available' and has no attachments

Anything else is skipped and written to the delete report.

Default mode is DRY RUN. Add --execute to really delete (you will be asked to
type the account name to confirm).

Examples
  python3 delete_snapshotted_volumes.py --account usmg-dev --report snapshot_report_usmg-dev_20261020_101500.csv
  python3 delete_snapshotted_volumes.py --account usmg-dev --report snapshot_report_usmg-dev_20261020_101500.csv --execute
"""
import argparse
import csv
import datetime as dt
import sys
from collections import defaultdict

import boto3
from botocore.exceptions import ClientError

FIELDS = ["account_name", "account_id", "region", "volume_id", "volume_name", "k8s_cluster",
          "snapshot_id", "snapshot_state", "volume_state", "status", "message"]


def log(msg):
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


def check_and_delete(ec2, row, execute):
    out = {k: row.get(k, "") for k in FIELDS}
    out.update(status="", message="", snapshot_state="", volume_state="")
    vid, sid = row["volume_id"], row["snapshot_id"]

    # 1 + 2: snapshot must be completed and belong to this volume
    try:
        snap = ec2.describe_snapshots(SnapshotIds=[sid])["Snapshots"][0]
    except ClientError as e:
        out.update(status="SKIPPED", message=f"Snapshot check failed: {e.response['Error']['Code']}")
        return out
    out["snapshot_state"] = snap["State"]
    if snap["VolumeId"] != vid:
        out.update(status="SKIPPED", message=f"Snapshot belongs to {snap['VolumeId']}, not {vid}")
        return out
    if snap["State"] != "completed":
        out.update(status="SKIPPED", message="Snapshot not completed yet - run again later")
        return out

    # 3: volume must still be unattached
    try:
        vol = ec2.describe_volumes(VolumeIds=[vid])["Volumes"][0]
    except ClientError as e:
        if e.response["Error"]["Code"] == "InvalidVolume.NotFound":
            out.update(status="ALREADY_DELETED", message="Volume no longer exists")
        else:
            out.update(status="ERROR", message=str(e))
        return out
    out["volume_state"] = vol["State"]
    if vol["State"] != "available" or vol.get("Attachments"):
        inst = ";".join(a["InstanceId"] for a in vol.get("Attachments", []))
        out.update(status="SKIPPED", message=f"Volume is now in use ({vol['State']}) {inst}".strip())
        return out

    try:
        ec2.delete_volume(VolumeId=vid, DryRun=not execute)
        out.update(status="DELETED")
    except ClientError as e:
        if e.response["Error"]["Code"] == "DryRunOperation":
            out.update(status="WOULD_DELETE", message="Dry run OK (permissions verified)")
        else:
            out.update(status="ERROR", message=str(e))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--account", required=True, choices=["usmg-dev", "usmg-test", "usmg-prod"])
    p.add_argument("--report", required=True, help="snapshot_report_<account>_*.csv from step 1 (not a _DRYRUN one)")
    p.add_argument("--profile", help="AWS CLI profile to use (optional)")
    p.add_argument("--execute", action="store_true", help="Really delete volumes (default: dry run)")
    p.add_argument("--yes", action="store_true", help="Skip the typed confirmation (for automation)")
    args = p.parse_args()

    if "_DRYRUN" in args.report:
        sys.exit("ABORT: that is a dry-run report (no snapshots were made). Use the report from the --execute run.")

    with open(args.report, newline="") as f:
        all_rows = list(csv.DictReader(f))
    rows = [r for r in all_rows if r["account_name"] == args.account and r.get("snapshot_id")]
    if not rows:
        sys.exit(f"No volumes with a snapshot id for {args.account} in {args.report}")
    ids = {r["account_id"] for r in rows}
    if len(ids) != 1:
        sys.exit(f"More than one account id in report: {ids}")
    expected = ids.pop()

    session = boto3.Session(profile_name=args.profile) if args.profile else boto3.Session()
    actual = session.client("sts").get_caller_identity()["Account"]
    if actual != expected:
        sys.exit(f"ABORT: credentials are for account {actual}, but report is for {args.account} ({expected})")

    mode = "EXECUTE - VOLUMES WILL BE DELETED" if args.execute else "DRY RUN"
    log(f"Account {args.account} ({actual}) - {len(rows)} volume(s) with snapshots - mode: {mode}")

    if args.execute and not args.yes:
        answer = input(f"Type the account name '{args.account}' to confirm deletion: ").strip()
        if answer != args.account:
            sys.exit("Not confirmed - nothing deleted.")

    clients, results = {}, []
    for n, row in enumerate(rows, 1):
        region = row["region"]
        if region not in clients:
            clients[region] = session.client("ec2", region_name=region)
        r = check_and_delete(clients[region], row, args.execute)
        results.append(r)
        log(f"[{n}/{len(rows)}] {r['volume_id']:<22} {r['status']:<16} {r['snapshot_id']} {r['message']}")

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = f"delete_report_{args.account}_{ts}{'' if args.execute else '_DRYRUN'}.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(results)

    counts = defaultdict(int)
    for r in results:
        counts[r["status"]] += 1
    log("Summary:")
    for k, v in sorted(counts.items()):
        log(f"  {k:<16} {v}")
    log(f"Report written: {out}")
    if counts.get("ERROR"):
        sys.exit(1)


if __name__ == "__main__":
    main()
