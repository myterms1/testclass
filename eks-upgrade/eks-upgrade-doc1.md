EKS 1.34 → 1.36 Upgrade Review & Runbook

Summary
The metal EKS clusters run Kubernetes 1.34 and can move to 1.36 in two in-place hops (1.34 → 1.35 → 1.36) by changing eks_version in two tfvars files per environment. Most components follow that value automatically; four things need work first.
• Golden AMIs for 1.35 and 1.36 (Linux AL2023 and Windows 2022) must be published, or the eks-nodes plan fails.
• Cluster Autoscaler runs 1.33 today (chart 9.51.0) and must be bumped to match each cluster version.
• Kyverno chart 3.5.2 (Kyverno 1.15) is outside its supported Kubernetes range and fails closed, so it must be upgraded.
• CoreDNS and kube-proxy patches will likely be overwritten when their EKS add-ons upgrade, breaking AD DNS for Windows pods until eks-addons is re-applied.
Every repo in the chain was verified against the exact git tag it is deployed at, including gsm-eks-automation v4.0.0 and gsm-eks-cluster v8.0.0 (see Verification status). Diagrams appear in each section; copy-ready Mermaid code for mermaid.live is in the Appendix.
How the six repos connect
gsm-metal is the entry point: a Terragrunt project whose four EKS stacks run in the order below, each pulling shared modules by git tag.
flowchart TD
    E["gsm-metal<br/>module/aws"]
    E --> S1["1. eks-cluster stack"]
    E --> S2["2. eks-nodes stack"]
    E --> S3["3. eks-addons stack"]
    E --> S4["4. eks-apps stack"]
    S1 --> AC["eks-automation//cluster<br/>v4.0.0"]
    AC --> CR["eks-cluster v8.0.0<br/>control plane"]
    S2 --> AL["eks-automation//linux_nodes<br/>+ //windows_nodes v4.0.0"]
    AL --> CNI["eks-cluster//aws_cni<br/>v8.0.0"]
    AL --> NG["gsm-eks-node-group<br/>v8.0.0"]
    S2 --> EA["eks-cluster//eks-addons<br/>v8.0.0"]
    S3 --> AD15["gsm-eks-addons<br/>blue v15.7.0"]
    AD15 --> H19["terraform-helm v19.4.0"]
    S4 --> AD14["gsm-eks-addons v14.9.0"]
    AD14 --> H18["terraform-helm v18.8.0"]
Stack (in gsm-metal)
Calls (verified tags)
Builds
eks-cluster
gsm-eks-automation//cluster v4.0.0 → gsm-eks-cluster v8.0.0 root module
EKS control plane, access entries, security groups, KMS grants, OIDC
eks-nodes
gsm-eks-automation//linux_nodes v4.0.0 → gsm-eks-cluster//modules/aws_cni v8.0.0 + gsm-eks-node-group v8.0.0
VPC CNI add-on, Linux node groups
eks-nodes
gsm-eks-automation//windows_nodes v4.0.0 → gsm-eks-node-group v8.0.0
Windows node groups
eks-nodes
gsm-eks-cluster//modules/eks-addons v8.0.0
coredns, kube-proxy, ebs-csi, pod-identity-agent, snapshot-controller
eks-addons (blue)
gsm-eks-addons v15.7.0 → gsm-terraform-helm v19.4.0
Infrastructure Helm charts, CoreDNS and kube-proxy ConfigMap patches
eks-addons (green)
gsm-eks-addons v15.5.0 → gsm-terraform-helm v19.2.0
Same, for the green cluster
eks-apps
gsm-eks-addons v14.9.0 → gsm-terraform-helm v18.8.0
TCS and Workflow app charts
gsm-eks and gsm-eks-iam-rbac were in the upload but nothing in this chain references them, so they are out of scope for the upgrade.
eks-apps stays on the older gsm-eks-addons 14.x line on purpose: it pins Helm provider = 2.17, while 15.x needs Helm provider >= 3.0. That is tech debt, not an upgrade blocker. The chart versions that matter (autoscaler, Kyverno, ingress-nginx) are identical across terraform-helm v18.8.0, v19.2.0 and v19.4.0.
Where the cluster version is set
The version (1.34 today) lives in exactly two files, and both apply to all nine environments (cdv, dev, dst, int, pvs, trn, pfx, rel, prd).
File
Key
Controls
gsm-metal/module/aws/eks-cluster/env-config/common.tfvars
params.blue.eks_version, params.green.eks_version
Control plane
gsm-metal/module/aws/eks-nodes/env-config/common.tfvars
params.blue.eks_version, params.green.eks_version
Node AMIs and kubelet
The env.hcl files use merge_strategy = "deep", so one environment can be upgraded at a time. Add the override in the environment file of both stacks:
# eks-cluster/env-config/us-east-1/dev.tfvars  AND  eks-nodes/env-config/us-east-1/dev.tfvars
params = {
  blue = {
    eks_version = "1.35"
  }
}
Move the value into both common.tfvars files only after every environment is done, and remove the per-environment overrides then.
What upgrades automatically and what needs work
The control plane, VPC CNI, managed add-ons and node AMIs all follow eks_version; two Helm charts and one ConfigMap template do not.
flowchart LR
    V["eks_version in tfvars"] --> CP["Control plane"]
    CP --> AO["addon-latest lookup<br/>vs live cluster version"]
    AO --> CNI["VPC CNI"]
    AO --> MA["coredns, kube-proxy,<br/>ebs-csi, pod-identity,<br/>snapshot-controller"]
    V --> AMI["AMI name lookup<br/>golden-...-eks-1-35-*"]
    AMI --> N["Linux + Windows nodes"]
    M["Manual changes"] --> CA["Cluster Autoscaler"]
    M --> KY["Kyverno"]
    M --> KP["kube-proxy template<br/>WinDSR gate"]
Component
Defined in
Follows the bump?
Action
EKS control plane
gsm-eks-cluster → aws_eks_cluster.version
Yes
Change tfvars only
VPC CNI
gsm-eks-cluster/modules/aws_cni (addon-latest)
Yes
None
coredns, kube-proxy, ebs-csi, pod-identity-agent, snapshot-controller
gsm-eks-cluster/modules/eks-addons (addon-latest)
Yes
Manage the ConfigMap overwrite (change 4)
Linux node AMI
gsm-eks-node-group: golden-gsm-al2023-aws-eks-1-35-*
Yes, if the AMI exists
Verify the AMI (change 1)
Windows node AMI
gsm-eks-node-group/modules/windows_support: golden-gsm-win2022-eks-1-35-*
Yes, if the AMI exists
Verify the AMI (change 1)
Cluster Autoscaler
gsm-terraform-helm v19.4.0 (blue), chart 9.51.0
No
Bump (change 2)
Kyverno
gsm-terraform-helm v19.4.0 (blue), chart 3.5.2
No
Bump (change 3)
kube-proxy custom config
gsm-eks-addons template
No
Remove WinDSR gate (change 5)
ALB controller 1.13.4, cert-manager 1.18.2, external-secrets 0.20.2, metrics-server 3.13.0, fluent-bit
gsm-terraform-helm
Not version-bound
Check with pluto; no known blockers
ingress-nginx 4.13.3
gsm-terraform-helm
Works
Plan a migration separately
addon-latest resolves through data.aws_eks_addon_version against the live cluster version, so add-ons move only when eks-nodes is re-applied after the control plane upgrade.
Required changes, most important first
Six items, checked against the deployed tags. Items 1–5 need action; item 6 was verified clean.
1. Golden AMIs must exist for 1.35 and 1.36
gsm-eks-node-group looks up AMIs by name with the Kubernetes version inside it, so a missing AMI makes the eks-nodes plan fail. Check before anything else:
# Prod-owned golden AMIs (all envs except dst)
aws ec2 describe-images --owners 382358134926 \
  --filters "Name=name,Values=golden-gsm-al2023-aws-eks-1-35-*" "Name=state,Values=available" \
  --query 'Images[].Name'
aws ec2 describe-images --owners 382358134926 \
  --filters "Name=name,Values=golden-gsm-win2022-eks-1-35-*" "Name=state,Values=available" \
  --query 'Images[].Name'

# dst uses dev golden AMIs (use_dev_golden_ami = true)
aws ec2 describe-images --owners 058264473556 \
  --filters "Name=name,Values=dev-golden-gsm-*-eks-1-35-*" --query 'Images[].Name'
Repeat with 1-36 before the second hop.
2. Bump Cluster Autoscaler
Chart 9.51.0 ships autoscaler 1.33.0; 9.52.0 moved to 1.34.0 and the 9.54.x line ships 1.35.0 (autoscaler issue #9057). So 1.34 clusters run autoscaler 1.33 today. Override it without releasing shared repos, in gsm-metal/module/aws/eks-addons/env-config/common.tfvars under params.blue.helm_charts (and green):
cluster-autoscaler = {
  chart_version = "9.54.x"      # exact latest 9.54.* patch
  values = {
    "image.tag" = "v1.35.x"     # latest 1.35 patch; v1.36.x on the next hop
  }
}
3. Upgrade Kyverno
Chart 3.5.2 is Kyverno 1.15, which Kyverno supports on Kubernetes 1.30–1.33 only (Kyverno install docs). Its webhooks fail closed by default, and gsm-eks-addons enables it with an image-registry restriction policy, so a broken Kyverno can block pod creation cluster-wide. Before each hop, move to a Kyverno line whose matrix covers the target version, overriding chart_version in the same tfvars file. Test in dev first; Kyverno upgrades can change CRDs and values.
4. CoreDNS and kube-proxy patches get overwritten
gsm-eks-cluster/modules/eks-addons sets resolve_conflicts_on_update = "OVERWRITE" on every add-on. gsm-eks-addons/k8s.tf separately patches the coredns ConfigMap (AD DNS forwarding for gMSA and Windows) and kube-proxy-config (Windows DSR, metrics bind address). Upgrading those add-ons will likely reset both to defaults, and AD name resolution fails until eks-addons is re-applied.
sequenceDiagram
    participant Op as Operator
    participant N as eks-nodes stack
    participant EKS as EKS add-on API
    participant CM as coredns ConfigMap
    participant A as eks-addons stack
    Op->>CM: Back up ConfigMaps
    Op->>N: Apply eks_version 1.35
    N->>EKS: Update coredns + kube-proxy
    EKS->>CM: OVERWRITE to defaults
    Note over CM: AD forwarding lost
    Op->>A: Apply immediately
    A->>CM: Re-apply AD forward blocks
    Op->>CM: Verify forward blocks
The runbook applies eks-addons right after eks-nodes to keep that window short. Verified in gsm-eks-cluster v8.0.0: OVERWRITE is hard-coded in modules/eks-addons/locals.tf for every add-on (and in modules/aws_cni for the VPC CNI), so it can't be changed from tfvars. The coredns add-on already receives configuration_values from that same file (only CPU and memory today), so the permanent fix is to add the AD forwarding Corefile there in a new gsm-eks-cluster release. Check the schema with aws eks describe-addon-configuration --addon-name coredns --addon-version <version>.
5. Remove the WinDSR feature gate
gsm-eks-addons/templates/kubeproxy-configmap-manifest.tpl.yaml sets featureGates: WinDSR: true in both deployed tags (v15.7.0 for blue, v15.5.0 for green). WinDSR has been GA since 1.34, and an upstream PR removes the gate, leaving DSR to winkernel.enableDSR (kubernetes PR #142125). The template already sets enableDSR: true, so delete the two featureGates lines; kube-proxy refuses to start with an unknown gate. Release it as gsm-eks-addons v15.7.1 and point both the blue and green ref= in gsm-metal/module/aws/eks-addons/addons.tf at it. The template's mode: iptables is correct.
6. Node bootstrap: verified, no change
Verified across gsm-eks-automation v4.0.0 and gsm-eks-node-group v8.0.0: no removed kubelet flags and no cgroup settings anywhere. Linux node groups default to ami_type = "CUSTOM" with the user-data-lt-golden.tpl.sh launch script (AL2023 NodeConfig). Windows node groups pass os_version (2022) as the AMI's Windows version and call AWS's Start-EKSBootstrap.ps1 with kubelet_args plus the tfvars kubelet_extra_args; neither contains --pod-infra-container-image. Only the golden AMI builds themselves remain outside this review (see the 1.35 table).
Kubernetes 1.35 and 1.36 changes against this setup
None of the upstream changes block this setup outright; two need confirmation from the AMI team (cgroup v2 on Linux, containerd 2.x on Windows). Source: EKS standard-support release notes.
Version
Change
Impact here
Action
1.35
cgroup v1 support removed; kubelet won't start on cgroup v1 by default
AL2023 uses cgroup v2 by default
Confirm the golden AMI didn't switch to v1
1.35
--pod-infra-container-image kubelet flag removed
Not in node-group code or tfvars
Code verified clean; confirm the golden AMI build
1.35
Last release supporting containerd 1.x
AL2023 EKS AMIs use containerd 2.1 since 1.34
Check Windows nodes: kubectl get nodes -o wide
1.35
ingress-nginx retired upstream (March 2026), no more fixes
TCS depends on it (header-buffer settings)
Plan migration separately; not a blocker
1.35
Windows Server 2025 supported
You run Windows 2022
Optional
1.36
IPVS mode removed from kube-proxy
You use mode: iptables
None
1.36
gitRepo volumes disabled
Not used
None
1.36
Strict IP/CIDR validation (no leading zeros, canonical CIDRs)
Values canonical, e.g. 172.20.0.0/16
Scan app values not reviewed here
1.36
containerd 2.x mandatory
Follows from 1.35 row
All nodes on 2.x before this hop
Cleanup items
These don't block the upgrade but are worth scheduling.
• gsm-terraform-helm/charts/local/fluent-bit-windows/templates/ still has autoscaling/v2beta2 HPA and PodSecurityPolicy templates. They don't render with current settings; delete them.
• gsm-eks-cluster/manifests/psp/ is dead PodSecurityPolicy code (PSP was removed in 1.25).
• addon-latest changes add-on versions on any re-apply. Pin explicit versions for prd.
• Blue eks-addons uses gsm-eks-addons v15.7.0 but green still uses v15.5.0. Align them when releasing v15.7.1.
• eks-apps uses gsm-eks-addons v14.9.0 (Helm provider 2.x) while eks-addons uses 15.x (provider 3.x). Converge on one line.
• The uploaded gsm-metal is on branch fixing_superset_userdata (August 2026), ahead of main (April 2026). Make the upgrade changes from whichever branch your pipeline deploys.
• gsm-eks and gsm-eks-iam-rbac are not referenced by this chain. gsm-eks sits on the same commit as gsm-eks-cluster v8.1.0, so it looks like a duplicate or renamed copy; consider archiving it.
Runbook
Four phases: prepare once, upgrade every environment to 1.35, repeat for 1.36, then finalize. Cluster names follow gsm-<env>-metal-eks-blue.
flowchart LR
    P0["Phase 0<br/>Preparation"] --> P1["Phase 1<br/>1.34 to 1.35"]
    P1 --> G1{"All 9 envs<br/>on 1.35?"}
    G1 -- No --> P1
    G1 -- Yes --> PR["1.36 prereqs<br/>AMIs, CA, Kyverno"]
    PR --> P2["Phase 2<br/>1.35 to 1.36"]
    P2 --> G2{"All 9 envs<br/>on 1.36?"}
    G2 -- No --> P2
    G2 -- Yes --> P3["Phase 3<br/>Finalize tfvars"]
Environment order for each hop:
flowchart LR
    subgraph DEV["Dev account"]
        cdv --> dev --> dst
    end
    subgraph TEST["Test account"]
        int --> pvs --> trn
    end
    subgraph PROD["Prod account"]
        pfx --> rel --> prd
    end
    dst --> int
    trn --> pfx
Phase 0: Preparation (once)
flowchart TD
    A["Check 1.35 golden AMIs"] --> B{"AMIs exist?"}
    B -- No --> B1["Ask AMI team, wait"]
    B1 --> A
    B -- Yes --> C["Release eks-addons v15.7.1<br/>without WinDSR gate"]
    C --> D["Add Autoscaler + Kyverno<br/>overrides in tfvars"]
    D --> E["Apply eks-addons in dev<br/>still on 1.34"]
    E --> F["Pre-flight checks<br/>insights, pluto, PDBs"]
    F --> G["Ready for Phase 1"]
1. Confirm the 1.35 golden AMIs exist (change 1).
2. Release gsm-eks-addons v15.7.1 without the WinDSR gate and bump ref= in gsm-metal/module/aws/eks-addons/addons.tf.
3. Add the Cluster Autoscaler and Kyverno overrides to eks-addons/env-config/common.tfvars, apply eks-addons in dev, and confirm both are healthy on 1.34.
4. Run pre-flight checks on each cluster:
aws eks list-insights --cluster-name gsm-dev-metal-eks-blue --region us-east-1
pluto detect-helm -o wide --target-versions k8s=v1.35.0
kubectl get pdb -A          # a PDB allowing 0 disruptions blocks node drains
kubectl get nodes -o wide   # containerd 2.x on Windows nodes
Phase 1: 1.34 → 1.35 (per environment)
flowchart TD
    S1["1. Back up coredns +<br/>kube-proxy ConfigMaps"] --> S2["2. eks-cluster tfvars 1.35<br/>plan + apply"]
    S2 --> C1{"Plan shows only<br/>version change?"}
    C1 -- No --> X["Stop, investigate"]
    C1 -- Yes --> S3["3. eks-nodes tfvars 1.35<br/>plan + apply"]
    S3 --> S4["4. Apply eks-addons<br/>immediately"]
    S4 --> S5["5. Plan eks-apps<br/>expect no changes"]
    S5 --> S6["6. Validate nodes, pods,<br/>add-ons, AD DNS, ingress"]
    S6 --> C2{"All checks pass?"}
    C2 -- No --> R["Restore ConfigMaps,<br/>fix, re-validate"]
    R --> S6
    C2 -- Yes --> NX["Next environment"]
1. Back up the ConfigMaps.
kubectl -n kube-system get cm coredns -o yaml > coredns-<env>.yaml
kubectl -n kube-system get cm kube-proxy-config -o yaml > kube-proxy-<env>.yaml
2. Control plane. In eks-cluster/env-config/us-east-1/<env>.tfvars, set eks_version = "1.35" under params.blue. The plan must show only the version change on aws_eks_cluster; stop if it shows a replacement. Apply (about 10–20 minutes; workloads keep running).
3. Nodes and managed add-ons. In eks-nodes/env-config/us-east-1/<env>.tfvars, set eks_version = "1.35" under params.blue. Expect new AMI IDs in launch templates, rolling node group updates, and new VPC CNI and add-on versions. Apply; Windows nodes take longest.
4. Helm add-ons, immediately. Plan and apply eks-addons. This restores the CoreDNS AD forwarding and kube-proxy config and rolls the autoscaler to 1.35.
5. Apps. Plan eks-apps; expect no changes, apply if there are.
6. Validate.
kubectl get nodes -o wide                                         # all v1.35.x
kubectl get pods -A | grep -v -E "Running|Completed"              # nothing stuck
aws eks list-addons --cluster-name gsm-<env>-metal-eks-blue
kubectl -n kube-system get cm coredns -o yaml | grep -A3 forward  # AD blocks present
Then test AD name resolution from a Windows pod, the TCS and Workflow URLs through ingress, and a scale-up to confirm the autoscaler.
Phase 2: 1.35 → 1.36
Repeat Phase 1 with "1.36" after these prerequisites:
[ ] 1.36 golden AMIs exist (Linux and Windows, prod and dev owners)
[ ] Autoscaler chart and image.tag changed to the 1.36 line
[ ] Kyverno version supports 1.36
[ ] Every node, including Windows, runs containerd 2.x
Phase 3: Finalize
Once all environments run 1.36, move eks_version = "1.36" into both common.tfvars files, remove the per-environment overrides, and set green to "1.36" so a future green cluster doesn't start old.
Alternative for production: blue/green
Every stack already supports green. For prd, enable green directly at 1.36, deploy apps, switch DNS, then retire blue. This skips the in-place 1.35 hop and gives instant rollback, at the cost of two clusters running for a while.
flowchart LR
    B["blue on 1.35"] --> G["Enable green at 1.36<br/>all 4 stacks"]
    G --> V["Deploy apps + validate"]
    V --> D["Switch DNS to green"]
    D --> C{"Healthy?"}
    C -- No --> RB["Switch DNS back to blue"]
    C -- Yes --> R["Retire blue"]
Verification status
The code review is complete: every module in the chain was checked at its deployed tag. What remains are runtime facts that only the AWS accounts and the AMI team can confirm.
Item
Status
How it was checked
gsm-eks-automation v4.0.0 module refs
Verified
cluster → gsm-eks-cluster v8.0.0; linux_nodes → aws_cni v8.0.0 + gsm-eks-node-group v8.0.0; windows_nodes → gsm-eks-node-group v8.0.0
Removed kubelet flags, cgroup settings
Verified clean
Searched gsm-eks-automation v4.0.0 and gsm-eks-node-group v8.0.0
Managed add-on behavior
Verified
gsm-eks-cluster v8.0.0: addon-latest resolves against the live cluster version; OVERWRITE hard-coded
Helm chart versions
Verified
terraform-helm v18.8.0, v19.2.0, v19.4.0 all pin autoscaler 9.51.0, Kyverno 3.5.2
WinDSR feature gate
Present, must fix
gsm-eks-addons v15.5.0 and v15.7.0 templates
Still to confirm outside the code:
[ ] 1.35 and 1.36 golden AMIs published (Linux and Windows, prod and dev owners)
[ ] Golden AMIs use cgroup v2 (Linux) and containerd 2.x (Linux and Windows)
[ ] aws eks list-insights shows no blocking findings per cluster
Appendix: Mermaid code for mermaid.live
Each block below is the plain-text source of one diagram in this doc. Copy a whole block, paste it into the Code pane at mermaid.live, and the diagram renders on the right.
#
Diagram
Section
D1
Repo dependency map
How the six repos connect
D2
What follows eks_version
What upgrades automatically
D3
CoreDNS overwrite sequence
Required changes, item 4
D4
Overall upgrade journey
Runbook
D5
Environment rollout order
Runbook
D6
Phase 0: Preparation
Runbook
D7
Phase 1: per-environment upgrade
Runbook
D8
Blue/green alternative
Runbook
D1: Repo dependency map
flowchart TD
    E["gsm-metal<br/>module/aws"]
    E --> S1["1. eks-cluster stack"]
    E --> S2["2. eks-nodes stack"]
    E --> S3["3. eks-addons stack"]
    E --> S4["4. eks-apps stack"]
    S1 --> AC["eks-automation//cluster<br/>v4.0.0"]
    AC --> CR["eks-cluster v8.0.0<br/>control plane"]
    S2 --> AL["eks-automation//linux_nodes<br/>+ //windows_nodes v4.0.0"]
    AL --> CNI["eks-cluster//aws_cni<br/>v8.0.0"]
    AL --> NG["gsm-eks-node-group<br/>v8.0.0"]
    S2 --> EA["eks-cluster//eks-addons<br/>v8.0.0"]
    S3 --> AD15["gsm-eks-addons<br/>blue v15.7.0"]
    AD15 --> H19["terraform-helm v19.4.0"]
    S4 --> AD14["gsm-eks-addons v14.9.0"]
    AD14 --> H18["terraform-helm v18.8.0"]
D2: What follows eks_version
flowchart LR
    V["eks_version in tfvars"] --> CP["Control plane"]
    CP --> AO["addon-latest lookup<br/>vs live cluster version"]
    AO --> CNI["VPC CNI"]
    AO --> MA["coredns, kube-proxy,<br/>ebs-csi, pod-identity,<br/>snapshot-controller"]
    V --> AMI["AMI name lookup<br/>golden-...-eks-1-35-*"]
    AMI --> N["Linux + Windows nodes"]
    M["Manual changes"] --> CA["Cluster Autoscaler"]
    M --> KY["Kyverno"]
    M --> KP["kube-proxy template<br/>WinDSR gate"]
D3: CoreDNS overwrite sequence
sequenceDiagram
    participant Op as Operator
    participant N as eks-nodes stack
    participant EKS as EKS add-on API
    participant CM as coredns ConfigMap
    participant A as eks-addons stack
    Op->>CM: Back up ConfigMaps
    Op->>N: Apply eks_version 1.35
    N->>EKS: Update coredns + kube-proxy
    EKS->>CM: OVERWRITE to defaults
    Note over CM: AD forwarding lost
    Op->>A: Apply immediately
    A->>CM: Re-apply AD forward blocks
    Op->>CM: Verify forward blocks
D4: Overall upgrade journey
flowchart LR
    P0["Phase 0<br/>Preparation"] --> P1["Phase 1<br/>1.34 to 1.35"]
    P1 --> G1{"All 9 envs<br/>on 1.35?"}
    G1 -- No --> P1
    G1 -- Yes --> PR["1.36 prereqs<br/>AMIs, CA, Kyverno"]
    PR --> P2["Phase 2<br/>1.35 to 1.36"]
    P2 --> G2{"All 9 envs<br/>on 1.36?"}
    G2 -- No --> P2
    G2 -- Yes --> P3["Phase 3<br/>Finalize tfvars"]
D5: Environment rollout order
flowchart LR
    subgraph DEV["Dev account"]
        cdv --> dev --> dst
    end
    subgraph TEST["Test account"]
        int --> pvs --> trn
    end
    subgraph PROD["Prod account"]
        pfx --> rel --> prd
    end
    dst --> int
    trn --> pfx
D6: Phase 0, preparation
flowchart TD
    A["Check 1.35 golden AMIs"] --> B{"AMIs exist?"}
    B -- No --> B1["Ask AMI team, wait"]
    B1 --> A
    B -- Yes --> C["Release eks-addons v15.7.1<br/>without WinDSR gate"]
    C --> D["Add Autoscaler + Kyverno<br/>overrides in tfvars"]
    D --> E["Apply eks-addons in dev<br/>still on 1.34"]
    E --> F["Pre-flight checks<br/>insights, pluto, PDBs"]
    F --> G["Ready for Phase 1"]
D7: Phase 1, per-environment upgrade
flowchart TD
    S1["1. Back up coredns +<br/>kube-proxy ConfigMaps"] --> S2["2. eks-cluster tfvars 1.35<br/>plan + apply"]
    S2 --> C1{"Plan shows only<br/>version change?"}
    C1 -- No --> X["Stop, investigate"]
    C1 -- Yes --> S3["3. eks-nodes tfvars 1.35<br/>plan + apply"]
    S3 --> S4["4. Apply eks-addons<br/>immediately"]
    S4 --> S5["5. Plan eks-apps<br/>expect no changes"]
    S5 --> S6["6. Validate nodes, pods,<br/>add-ons, AD DNS, ingress"]
    S6 --> C2{"All checks pass?"}
    C2 -- No --> R["Restore ConfigMaps,<br/>fix, re-validate"]
    R --> S6
    C2 -- Yes --> NX["Next environment"]
D8: Blue/green alternative
flowchart LR
    B["blue on 1.35"] --> G["Enable green at 1.36<br/>all 4 stacks"]
    G --> V["Deploy apps + validate"]
    V --> D["Switch DNS to green"]
    D --> C{"Healthy?"}
    C -- No --> RB["Switch DNS back to blue"]
    C -- Yes --> R["Retire blue"]
For Phase 2 (1.35 → 1.36), reuse D7 and replace 1.35 with 1.36 in the labels.
