This plan is safe to apply. It's exactly what we expected.

**The actual change (Image 7):**

```
aws_eks_cluster.eks will be updated in-place
  ~ version = "1.34" -> "1.35"
```

It's **updated in-place**, not replaced, and the version is the only attribute changing. This is the control plane upgrade.

**The plan summary, "2 to add, 1 to change, 1 to destroy":**

| Plan line | What it is | Concern? |
|---|---|---|
| **1 to change**: `aws_eks_cluster.eks` | The 1.34 → 1.35 upgrade | ✅ This is what you want |
| **1 add**: `local_file.kubeconfig` | A temporary kubeconfig file on the pipeline runner. Recreated on every run because the runner starts fresh | No |
| **1 add + 1 destroy**: `null_resource.validate_kubectl` | A timestamp-triggered check that re-runs on every apply. Its trigger changes each time, so Terraform replaces it | No. It's a script check, not real infrastructure |

**The "Objects have changed outside of Terraform" section (Images 1–3)** is informational only; Terraform isn't going to change any of it:

- `platform_version "eks.5" -> "eks.32"`: AWS has applied its own patch updates to your 1.34 control plane over time. That's normal.
- `control_plane_scaling_config`, `kube_api_server_config`, `kube_scheduler_config`, `control_plane_egress_mode` and the other `+` blocks are settings AWS now reports for every cluster, showing their current default values. Your newer AWS provider version simply reads them now. The actual plan (Image 7) confirms they're untouched ("9 unchanged blocks hidden").
- `local_file.kubeconfig has been deleted`: the file from the last run no longer exists on the new runner. That's normal and the file is recreated.

**The data sources (Images 3–6)** are just reads that happen during apply (cluster details, auth token, and the `check-aws-cni-pods.sh` script). Nothing changes there.

**Apply it.** It takes about 10–20 minutes. Afterwards, confirm:

```bash
aws eks describe-cluster --name gsm-dst-metal-eks-blue --query cluster.version
# expected: "1.35"
```

**Before you run `eks-nodes` for `dst`:**

1. Confirm the Windows AMI `dev-golden-gsm-win2022-eks-1-35-*` exists in account `058264473556`. You've confirmed the Linux one already.
2. Back up the ConfigMaps:
   ```bash
   kubectl -n kube-system get cm coredns -o yaml > coredns-dst.yaml
   kubectl -n kube-system get cm kube-proxy-config -o yaml > kube-proxy-dst.yaml
   ```

Send the `eks-nodes` plan when you have it and I'll review it the same way.