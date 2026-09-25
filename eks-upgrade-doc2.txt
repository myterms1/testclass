These are two tools installed in your cluster by Terraform. Each one has to be compatible with your Kubernetes version:

- **Cluster Autoscaler** adds and removes nodes. Its version must match your Kubernetes version (1.35 autoscaler for a 1.35 cluster). Yours is 1.33 today.
- **Kyverno** checks every pod before it starts. If it's too old for your cluster, it can stop new pods from starting. Yours only officially supports up to Kubernetes 1.33.

You don't need to edit the shared repos to fix this. Your tfvars file already overrides chart settings; you just add two more entries.

**Where:** `gsm-metal/module/aws/eks-addons/env-config/common.tfvars`, inside the existing `helm_charts = { ... }` block under `blue` (the same place you already have `cluster-overprovisioner-linux`, `descheduler`, and so on).

**What to add:**

```hcl
    helm_charts = {
      cluster-autoscaler = {
        chart_version = "9.54.0"          # chart that ships autoscaler 1.35
        values = {
          "image.tag" = "v1.35.0"         # must match cluster version
        }
      }
      kyverno = {
        chart_version = "<see below>"     # a Kyverno version that supports 1.35
      }

      # ... your existing entries stay as they are ...
      cluster-overprovisioner-linux = {
```

**How to get the exact version numbers.** Run these on your machine:

```bash
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update

helm search repo autoscaler/cluster-autoscaler --versions | head -15
helm search repo kyverno/kyverno --versions | head -15
```

Each output has two columns you care about:

- **CHART VERSION** goes in `chart_version`.
- **APP VERSION** is the actual tool version.

To pick the right rows:

- **Cluster Autoscaler:** pick the newest row where APP VERSION starts with **1.35**. For example, chart 9.54.x has app version 1.35.0.
- **Kyverno:** pick a row whose APP VERSION supports Kubernetes 1.35. Check the compatibility table at kyverno.io/docs/installation. Only use a 1.16 release if that table lists 1.35 support for it.

When you later upgrade to 1.36, repeat this and pick the rows for 1.36.

If you paste the output of those two `helm search` commands here, I'll tell you the exact numbers to put in.


==========================================================================================================================================================
You're right: they aren't in `gsm-metal`, and that's expected. They're turned on by default in the shared repos, so every application repo that uses them (like `gsm-metal`) gets them automatically without listing them.

## Where they actually live

```
gsm-metal  (eks-addons stack)
   │  does NOT mention autoscaler or kyverno
   ▼
gsm-eks-addons v15.7.0 → helm.tf
   │  cluster-autoscaler = { enabled = true }   (line ~102)
   │  kyverno            = { enabled = true }   (line ~165)
   ▼
gsm-terraform-helm v19.4.0 → locals.tf
      cluster-autoscaler chart_version = "9.51.0"   ← the version that needs changing
      kyverno            chart_version = "3.5.2"    ← the version that needs changing
```

So the versions that need changing are in `gsm-terraform-helm/locals.tf`.

## Two ways to change them

**Option A: fix it in the shared repo.** This fixes it for every application cluster that uses these repos.

1. In `gsm-terraform-helm/locals.tf`, change the `chart_version` for `cluster-autoscaler` and `kyverno`, and release a new tag (for example `v19.4.1`).
2. In `gsm-eks-addons/helm.tf`, point to that new terraform-helm tag. You're already releasing a new `gsm-eks-addons` tag for the WinDSR fix, so do both in the same release (`v15.7.1`).
3. In `gsm-metal/module/aws/eks-addons/addons.tf`, change `ref=` to `v15.7.1`.

**Option B: override it only for metal.** Nothing in the shared repos changes. `gsm-eks-addons` lets an application repo override any default: whatever you put in `helm_charts` in `gsm-metal` wins over the shared default, and anything you leave out keeps the shared value. So adding the two entries from my previous message to `gsm-metal/module/aws/eks-addons/env-config/common.tfvars` changes only the version, and everything else (enabled, IAM role, Kyverno policies) stays as the shared repos define it.

## Which to choose

Since you own the shared repos and other application clusters will need the same EKS upgrade, **Option A is the better choice**: you make one change and every cluster benefits. Use Option B only if you want to test in metal first without affecting other teams.

With Option A, the complete list of required changes becomes:

| Repo | File | Change |
|---|---|---|
| `gsm-terraform-helm` | `locals.tf` | Autoscaler and Kyverno `chart_version`; new tag |
| `gsm-eks-addons` | `helm.tf` | Point to the new terraform-helm tag |
| `gsm-eks-addons` | `templates/kubeproxy-configmap-manifest.tpl.yaml` | Delete the 2 WinDSR lines; release `v15.7.1` |
| `gsm-metal` | `eks-addons/addons.tf` | `ref=v15.7.1` (blue and green) |
| `gsm-metal` | `eks-cluster/.../common.tfvars` and `eks-nodes/.../common.tfvars` | `eks_version = "1.35"` |



==========================================================================================================================================================
Fair question. Neither bump is what performs the EKS upgrade, and your clusters will probably keep working without them. They're about avoiding hard-to-debug problems after the upgrade.

**Cluster Autoscaler**

The autoscaler decides when to add nodes. To make that decision, it runs its own copy of Kubernetes' scheduling logic to predict where pending pods would fit. That copy is built into the autoscaler, and each autoscaler release is built for one Kubernetes version, which is why their versions are numbered the same (autoscaler 1.35 for Kubernetes 1.35).

If the autoscaler is older than the cluster, its predictions can drift from how the real scheduler behaves. The autoscaler's own documentation warns that bugs from mismatched versions can be subtle. In practice, that looks like:

- pods stuck in `Pending` because the autoscaler thinks they fit somewhere they don't, so no node gets added
- nodes not scaling down because it misjudges where pods could move

You're already one version behind (autoscaler 1.33 on Kubernetes 1.34) and it's probably working. After two more upgrades you'd be three versions behind (1.33 on 1.36), and the risk grows with each version.

**Kyverno**

Kyverno checks every pod before it's allowed to start. Your setup uses it to block images from unapproved registries. The important detail is that **if Kyverno fails, pods are blocked instead of allowed**. So if an old Kyverno misbehaves on a newer Kubernetes, new pods may stop starting across the whole cluster: deployments, restarts, and new nodes all become affected.

Your Kyverno (1.15) is only tested up to Kubernetes 1.33. It might work fine on 1.35 and 1.36, but if it doesn't, the impact is large.

**In short:**

| | If you skip the bump | Likelihood | Impact |
|---|---|---|---|
| Autoscaler | Scaling mistakes, pods stuck pending | Grows with each version | Medium |
| Kyverno | New pods blocked cluster-wide | Low to medium | High |

Both are cheap insurance: a version number change in one file. If you want to keep things minimal, at least do Kyverno, then check the autoscaler after the upgrade in `dev`. If pending pods get nodes normally, you can bump the autoscaler later.



==========================================================================================================================================================
Here are the versions, with what I could confirm and what you need to check.

**Cluster Autoscaler**

| Kubernetes | Chart version | Image tag | Confirmed? |
|---|---|---|---|
| 1.34 (today) | 9.51.0 (yours) | v1.33.0 | Already mismatched |
| **1.35** | **9.54.x** | **v1.35.x** | Yes: cluster-autoscaler-chart-9.54.x → appVersion: 1.35.0 |
| **1.36** | Newer than 9.54 (latest is 9.59.0) | **v1.36.x** | Not confirmed. The latest published chart is 9.59.0, but I couldn't confirm which chart first ships 1.36 |

**Kyverno**

Kyverno chart versions follow a pattern: chart 3.5.x is Kyverno 1.15.x (your current 3.5.2), chart 3.6.x is 1.16.x, and chart 3.7.x is 1.17.x.

| Kubernetes | Kyverno version | Chart version | Confirmed? |
|---|---|---|---|
| 1.34 (today) | 1.15 (chart 3.5.2, yours) | | Outside supported range: 1.15.x supports Kubernetes 1.30 to 1.33 |
| **1.35** | **1.17.x** | **3.7.x** | Kyverno's table lists a release supporting Kubernetes 1.32 to 1.35. That row is labeled "1.16.x" twice on their site, which looks like a typo for 1.17.x |
| **1.36** | Probably 1.18.x | Probably 3.8.x | Not confirmed; Kyverno's table doesn't list 1.36 yet |

**Run this once to get the exact answers for both, including 1.36:**

```bash
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update
helm search repo autoscaler/cluster-autoscaler --versions | head -10
helm search repo kyverno/kyverno --versions | head -10
```

- For the autoscaler, pick the newest row whose APP VERSION starts with 1.35, and later 1.36.
- For Kyverno, pick the newest 3.7.x chart for 1.35. For 1.36, pick the chart for whichever Kyverno version the compatibility table lists as supporting 1.36.

Paste the output here and I'll give you the exact numbers.

**One caution about Kyverno:** going from chart 3.5 to 3.7 skips a version and changes the Kyverno CRDs and webhooks. Test it in `dev` on 1.34 first, before the EKS upgrade, and confirm pods still start normally.




==========================================================================================================================================================
Your output settles it.

**Cluster Autoscaler**

There's no chart yet that ships autoscaler 1.36: the newest chart, 9.59.0, still defaults to 1.35.0. So use the latest chart and set the image version yourself. The upstream releases list autoscaler 1.36.1 and 1.35.2 as the current patch releases.

| EKS version | `chart_version` | `image.tag` |
|---|---|---|
| **1.35** | `9.59.0` | `v1.35.2` |
| **1.36** | `9.59.0` (same chart) | `v1.36.1` |

**Kyverno**

Kyverno's charts follow a simple pattern, and each Kyverno release supports four Kubernetes versions, shifting up by one each release (1.15 supports 1.30–1.33, 1.16 supports 1.31–1.34, and so on). By that pattern, Kyverno 1.18 supports Kubernetes 1.33–1.36. That covers your current 1.34, plus 1.35 and 1.36, so you only change Kyverno once.

| EKS version | `chart_version` | Kyverno version |
|---|---|---|
| **1.34 (now), 1.35 and 1.36** | `3.8.2` | v1.18.2 |

Kyverno's website doesn't list 1.18 in its table yet, so this is based on the pattern. Confirm by checking that the v1.18 release notes on GitHub mention Kubernetes 1.36.

**What goes in the code.** In `gsm-terraform-helm/locals.tf`, set:

```hcl
cluster-autoscaler = {
  chart_version = "9.59.0"
  values = {
    "image.tag" = "v1.35.2"    # change to "v1.36.1" for the 1.36 upgrade
  }
  ...
}

kyverno = {
  chart_version = "3.8.2"
  ...
}
```

**Order:**

1. Upgrade **Kyverno first, on your current 1.34 clusters**, and test in `dev`. Going from chart 3.5 to 3.8 skips several releases, so read the upgrade notes for 3.6, 3.7 and 3.8 and confirm pods still start normally.
2. Upgrade the **autoscaler** together with the EKS upgrade (`v1.35.2` for 1.35, then `v1.36.1` for 1.36).





==========================================================================================================================================================
Good catch. There's no `image.tag` in your code because the image version comes from **inside the Helm chart itself**.

**How it works:**

Every Helm chart ships with a built-in `values.yaml` containing default settings, including which image to run. Your code only lists the settings you want to *change*. Anything you don't list uses the chart's default.

```
gsm-terraform-helm/locals.tf
  chart_version = "9.51.0"      ← you choose the chart version
  values = { awsRegion, resources, extraArgs, ... }   ← no image.tag here
          │
          ▼
Chart 9.51.0's built-in values.yaml
  image:
    repository: registry.k8s.io/autoscaling/cluster-autoscaler
    tag: v1.33.0                ← the image comes from here
```

So choosing `chart_version = "9.51.0"` also chooses the image, and that chart's default image is **v1.33.0**, not v1.34. That's why I said earlier that you're running autoscaler 1.33 on a 1.34 cluster.

**You can see it yourself:**

```bash
# What the chart defaults to
helm show values autoscaler/cluster-autoscaler --version 9.51.0 | grep -A4 "^image:"

# What is actually running in your cluster
kubectl get deploy -A -l app.kubernetes.io/name=aws-cluster-autoscaler \
  -o jsonpath='{..image}'
```

**Why you now need to add `image.tag`:**

Normally changing `chart_version` alone would be enough, because each chart release brings a newer default image. But no chart has been released with a 1.36 image yet; even the newest chart (9.59.0) defaults to 1.35.0. So you have to override the image by adding one line to your existing `values` block. Any value you add there overrides the chart's default.

```hcl
    cluster-autoscaler = {
      enabled          = false
      chart_repository = "https://kubernetes.github.io/autoscaler"
      chart_version    = "9.59.0"          # was 9.51.0

      ...

      values = {
        "image.tag"                                 = "v1.35.2"   # NEW line; "v1.36.1" for the 1.36 upgrade
        "awsRegion"                                 = local.params.region
        "autoDiscovery.clusterName"                 = local.params.eks_cluster_name
        # ... rest unchanged ...
      }
    }
```

Once a future chart ships with 1.36 as its default, you could remove the `image.tag` line and just update `chart_version`. Until then, the override is the only way to run autoscaler 1.36.




==========================================================================================================================================================
That confirms it: the chart default is `v1.33.0`, and that's exactly what's running. Your cluster is on EKS 1.34 with autoscaler 1.33, one version behind, because the image comes from the chart's default.

**What to do:**

| When | `chart_version` | `image.tag` (new line) |
|---|---|---|
| Now, or together with the 1.35 upgrade | `9.59.0` | `v1.35.2` |
| Together with the 1.36 upgrade | `9.59.0` | `v1.36.1` |

After each change, run the same `kubectl` command. It should show `cluster-autoscaler:v1.35.2`, and later `v1.36.1`.

Don't set `v1.35.2` while the cluster is still on 1.34. An autoscaler newer than the cluster can have the same mismatch problem in the other direction. Apply the autoscaler change in the same rollout as the EKS 1.35 upgrade, right after the control plane and nodes are upgraded.




==========================================================================================================================================================
No. `v1.35.2` is only the **Cluster Autoscaler's container image**, not your Linux nodes' image.

Your cluster has two different kinds of "images":

| What | What it is | Where its version comes from | Example |
|---|---|---|---|
| **Node image (AMI)** | The operating system your EC2 worker machines boot from (Linux AL2023 or Windows 2022) | `eks_version` in `eks-nodes` tfvars → picks the golden AMI by name | `golden-gsm-al2023-aws-eks-1-35-*` |
| **Container image** | One application running *inside* the cluster as a pod | That application's Helm chart | `cluster-autoscaler:v1.35.2` |

Here's how they fit together:

```
EC2 worker node  ← booted from the golden AMI (node image)
  └── pods running on it
        ├── cluster-autoscaler  ← container image v1.35.2
        ├── coredns
        ├── your TCS / Workflow apps
        └── ...
```

The Cluster Autoscaler is just one small app running as a pod. Its job is to watch for pods that can't be scheduled and add EC2 nodes when needed. The `v1.35.2` only says which version of that app runs.

**Your Linux nodes' image is handled separately and automatically.** When you set `eks_version = "1.35"` in the `eks-nodes` tfvars, the code looks up the golden AMI named `golden-gsm-al2023-aws-eks-1-35-*` and replaces the nodes with it. You don't set any image version for the nodes yourself; you only need to make sure your AMI team has published that 1.35 AMI.



==========================================================================================================================================================
