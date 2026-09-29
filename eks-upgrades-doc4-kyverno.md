## 1. With full downtime, is destroy group 2 / create group 1 OK?

Yes. With the cluster in announced downtime and no services running, the risk to apps is gone. Three things can still go wrong, and they affect the **pipeline**, not users:

| Risk | Does downtime remove it? | What to do |
|---|---|---|
| Apps affected while there are no policies | ✅ Yes | Nothing |
| Apply fails with *"name still in use"* (create runs before destroy) | ❌ No | Rerun the apply, which extends your window |
| Leftover Kyverno webhooks block **new pods**, including the other charts in the same apply (ALB, trust-manager, cert-manager). The apply can hang for up to the 1800s timeout | ❌ No | Check and delete leftover webhooks |
| Kyverno objects not managed by Terraform are lost (PolicyExceptions, etc.) | ❌ No | Back them up first |

So it's acceptable, including in prod with downtime, as long as you handle the last three. Your second idea handles them best.

## 2. Uninstall Kyverno manually before eks-addons

Yes, and it's actually cleaner than letting Terraform do it. When the Helm provider refreshes and finds the release gone, it drops `chart_group_2["kyverno"]` from state by itself (the plan shows it as "deleted outside of Terraform"). Terraform then only has to **create** group 1. There's no race and no "name in use" error, and Kyverno installs fresh at the new chart version.

Run these steps **during the downtime, right before the eks-addons pipeline**:

```bash
# 0. see what's there
helm -n security list | grep kyverno

# 1. back up Kyverno objects (in case something wasn't managed by Terraform)
kubectl get clusterpolicy,policy,policyexception -A -o yaml > kyverno-backup-$(date +%F).yaml

# 2. uninstall policies first, then Kyverno
helm -n security uninstall kyverno-addons --wait
helm -n security uninstall kyverno --wait

# 3. make sure nothing is left that can block pods
kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations | grep -i kyverno
#    if anything shows up:
#    kubectl delete validatingwebhookconfiguration <name>
#    kubectl delete mutatingwebhookconfiguration <name>

kubectl -n security get pods | grep -i kyverno     # should be empty
kubectl get crd | grep kyverno                     # usually gone; OK if some remain
```

Then run the **eks-addons pipeline**. The plan should show:
- no Kyverno releases being destroyed, only small leftovers inside the old module such as `time_sleep` and `null_resource`
- `chart_group_1["kyverno"]` main chart and `kyverno-addons` **will be created**
- everything else the same as before (ALB, trust-manager, etc.)

After the apply:
```bash
helm -n security list                    # kyverno + kyverno-addons deployed
kubectl -n security get pods             # kyverno pods Running
kubectl get clusterpolicy                # restrict-image-registries present
```

Add your 3.8.2 override now. Kyverno is installed fresh, so it goes straight onto the version that supports 1.36.

Add this uninstall step to the runbook for **every environment**, since each one has Kyverno in group 2. If you later want to skip the manual step, the `moved` block in terraform-helm still works. For now, uninstall plus downtime is a valid plan.
