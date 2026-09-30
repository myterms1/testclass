The likely cause is a change in **terraform-helm v20** that came in with the `v99.0.0` tag. It changed how the NLB health-checks ingress-nginx, and those changes were made for **Facets**, not Elements.

## What changed for ingress-nginx (v19.4.0 → v20.0.4)

| Setting | Before (worked) | Now |
|---|---|---|
| NLB health check port | `80` | **`10254`** |
| Proxy protocol | on (`use-proxy-protocol=true` + NLB proxy protocol `*`) | **off** |
| Preserve client IP | `true` | **`false`** |
| Extra TCP port | — | **`61616` → `batch/pricer-networx`** (Facets pricer, doesn't exist in Elements) |

Both targets (100.x pod IPs) now fail health checks. The most likely reason is that the NLB checks `http://<pod-ip>:10254/healthz`, and the **security group on the pod ENIs only allows 80/443, not 10254**. Before the upgrade the check used port 80, which was allowed.

## Confirm it (5 minutes)

```bash
TG=$(aws elbv2 describe-target-groups --names k8s-ingressc-ingressn-c974591727 \
     --query 'TargetGroups[0].TargetGroupArn' --output text)

# 1. health check settings: expect HTTP / 10254 / /healthz
aws elbv2 describe-target-groups --target-group-arns $TG \
  --query 'TargetGroups[0].[HealthCheckProtocol,HealthCheckPort,HealthCheckPath]'

# 2. why unhealthy
aws elbv2 describe-target-health --target-group-arn $TG \
  --query 'TargetHealthDescriptions[].[Target.Id,TargetHealth.Reason]' --output table
```

- **`Target.Timeout`** means the network or security group is blocking 10254. This is the most likely result. Go to Fix A.
- **`Target.ResponseCodeMismatch`** means the pod is reachable but `/healthz` isn't returning 200. Check the pods and logs:
  ```bash
  kubectl -n ingress-control get pods -o wide        # pod IPs should match 100.126.143.40 / 100.127.20.108, all Ready
  kubectl -n ingress-control logs deploy/aws-load-balancer-controller --since=1h | grep -iE "error|warn"
  ```

Find the security group on a target's ENI:
```bash
aws ec2 describe-network-interfaces \
  --filters Name=addresses.private-ip-address,Values=100.126.143.40 \
  --query 'NetworkInterfaces[].Groups' --output table
```
Look at that SG's inbound rules. If there's nothing for **TCP 10254** from the NLB subnets or VPC CIDR, that's your answer.

## Fix, pick one

**Fix A (proper fix):** allow TCP **10254** inbound on that pod SG from the NLB subnets or VPC CIDR. Do it in Terraform wherever that SG is defined (usmg-eks-cluster or the ENIConfig SG). Health checks should turn healthy within about 30 seconds. Port 10254 is ingress-nginx's real health endpoint, so this is the better long-term setting.

**Fix B (quick, Elements only):** override the port back to 80 in `usmg-elements/module/aws/eks-addons/env-config/us-east-1/dst.tfvars`, under `params.blue.helm_charts` → `ingress-nginx` → `values`. Copy the exact key from `locals.tf` in terraform-helm v20.0.4 (around line 1090):
```hcl
"controller.service.annotations.service\\.beta\\.kubernetes\\.io/aws-load-balancer-healthcheck-port" = "80"
```

With either fix, also remove the Facets pricer mapping for Elements. The chart comment says setting a value to `null` removes it:
```hcl
"tcp.61616"                       = null
"controller.service.ports.pricer" = null
```

## This affects every Elements environment

terraform-helm v20 contains **Facets-specific ingress changes**: no proxy protocol, client IP not preserved, and the pricer port. Every Elements environment you move to `v16.0.x` will get them. Once dst works, decide whether Elements keeps these settings. If apps rely on seeing the real client IP, Elements needs overrides for proxy protocol and preserve-client-IP too. Put that override block in `common.tfvars` so all environments get it.

Send me the output of the `describe-target-health` command and the SG inbound rules, and I'll confirm which fix applies.























Thanks, these two outputs change the picture:

- **The health check is still `HTTP / 80 / /healthz`.** The v20 setting (port 10254) never reached AWS, so the security-group-on-10254 theory is wrong.
- `Target.FailedHealthChecks` is the generic code a Network Load Balancer uses. Unlike an ALB, it doesn't tell you whether it was a timeout or a bad response. That was my mistake earlier.

## Most likely cause: proxy protocol mismatch

The upgrade changed **nginx** but not the **target group**:

| Side | Before | Now |
|---|---|---|
| ingress-nginx (`use-proxy-protocol`) | `true` | **`false`**, applied by Helm |
| NLB target group (`proxy_protocol_v2`) | enabled | **probably still enabled** |

The NLB still puts a proxy-protocol header in front of every connection. nginx no longer expects it, so it rejects both the health checks and your browser traffic. The unchanged health-check port suggests the load balancer controller didn't apply the new service settings at all.

## Confirm (2 commands)

```bash
# 1. is proxy protocol still on for the target group?
aws elbv2 describe-target-group-attributes --target-group-arn $TG \
  --query "Attributes[?Key=='proxy_protocol_v2.enabled' || Key=='preserve_client_ip.enabled']" \
  --output table

# 2. is nginx rejecting the NLB's connections?
kubectl -n ingress-control logs -l app.kubernetes.io/name=ingress-nginx --since=10m | grep -ciE "broken header| 400 "
```

If `proxy_protocol_v2.enabled` is **true** and you see 400s or "broken header", that confirms it.

## Fix to get the UI back now

Turn proxy protocol off on the target group to match nginx:
```bash
aws elbv2 modify-target-group-attributes --target-group-arn $TG \
  --attributes Key=proxy_protocol_v2.enabled,Value=false
```
Targets should turn healthy in about 30–60 seconds. The controller won't turn it back on, because the service annotation for proxy protocol is gone.

## Then find out why the controller didn't apply the settings

```bash
kubectl -n ingress-control describe svc ingress-nginx-controller | tail -20     # look for FailedDeployModel / errors
kubectl -n ingress-control logs deploy/aws-load-balancer-controller --since=3h | grep -iE "error|ingress-nginx"
```
The likely culprit is the Facets pricer port `61616` pointing at `batch/pricer-networx`, which doesn't exist in Elements. Removing it for Elements with the `null` overrides from my last message should let the controller reconcile cleanly. After that, the health check will move to 10254, and you may need that security group rule after all.

## Decide for Elements (before other environments)

This is really the question of whether Elements keeps the v20 (Facets) ingress behavior:
- **Keep v20 behavior:** no proxy protocol, client IP not preserved, health check on 10254. Remove the pricer port.
- **Keep the old Elements behavior:** override `use-proxy-protocol = "true"`, the proxy-protocol annotation `"*"`, `preserve_client_ip.enabled=true`, and health-check port `80` in `common.tfvars`. Apps keep seeing real client IPs.

Send me the output of the two confirm commands, and the controller errors if there are any.















=====
That confirms it. The target group still has the **old v19 settings**:

| Target group setting | Now | What the new chart expects |
|---|---|---|
| `proxy_protocol_v2.enabled` | **true** | false |
| `preserve_client_ip.enabled` | **true** | false |
| Health check port | **80** | 10254 |

nginx was switched to `use-proxy-protocol = false`, but the NLB still adds a proxy-protocol header to every connection. nginx doesn't expect it, so it rejects the connections, and the UI fails. All three settings are stale, which means the **AWS Load Balancer Controller never applied the new service settings**.

On your log check: with `-l`, kubectl only shows the **last 10 lines per pod**, so the count was too small to mean anything. Also, `--profile dev-admin` in the first line landed on `grep`, not kubectl. Use this:
```bash
kubectl -n ingress-control logs -l app.kubernetes.io/name=ingress-nginx -c controller \
  --since=10m --tail=-1 | grep -ciE "broken header| 400 "
```

## Step 1: restore the UI now

```bash
aws elbv2 modify-target-group-attributes --target-group-arn $TG \
  --attributes Key=proxy_protocol_v2.enabled,Value=false
```
Wait about 1 minute, then check:
```bash
aws elbv2 describe-target-health --target-group-arn $TG \
  --query 'TargetHealthDescriptions[].[Target.Id,TargetHealth.State]' --output table
```
Both targets should show **healthy**, and the UI should open. If they're still unhealthy, send me that output.

You can undo this at any time by setting `Value=true`.

## Step 2: find out why the controller is stuck

```bash
kubectl -n ingress-control get svc | grep ingress-nginx
kubectl -n ingress-control describe svc <ingress-nginx-controller-svc> | sed -n '/Events/,$p'
kubectl -n ingress-control logs deploy/aws-load-balancer-controller --since=6h --tail=-1 \
  | grep -iE "error|failed" | tail -20
```
Look for `FailedDeployModel` or errors mentioning port **61616** / pricer. That's my main suspect: the Facets pricer port is being added to a Service in Elements, where `batch/pricer-networx` doesn't exist.

## Step 3: make it permanent in code

Until the controller reconciles properly, the next change to that Service could flip settings again. Once you've seen the error from Step 2, add the Elements overrides:

- Remove the pricer port:
  ```hcl
  "tcp.61616"                       = null
  "controller.service.ports.pricer" = null
  ```
- Then choose one ingress mode for Elements:
  - **v20 mode:** no proxy protocol, client IP not preserved, health check on 10254. Needs TCP 10254 open on the pod security group.
  - **Old Elements mode:** `use-proxy-protocol = "true"`, proxy-protocol annotation `"*"`, `preserve_client_ip.enabled=true`, health check port 80.

Send me the Step 2 output, and I'll tell you exactly which override block to put in `dst.tfvars`.

=================

below is the fix:

The UI works because the target group and nginx now agree: both have proxy protocol **off**. Your service output also shows why the controller got stuck. The Service now has port **61616** (the Facets pricer), but the NLB still has only the **443** listener. The controller never managed to add that port, so it never applied the other new settings either.

The manual fix is fragile. The next time the controller does reconcile, it will apply the v20 settings, including the health check on **10254**, and that could break things again. Lock in what's working now in code.

## Make it permanent (dst)

In `usmg-elements/module/aws/eks-addons/env-config/us-east-1/dst.tfvars`, add these to the existing `ingress-nginx.values` block under **blue** (and under **green** too):

```hcl
      ingress-nginx = {
        addon_config = {
          dns_record_weight = "100"
        }
        values = {
          # Remove Facets-only pricer port (batch/pricer-networx doesn't exist in Elements)
          "tcp.61616"                       = null
          "controller.service.ports.pricer" = null

          # Keep the health check that works today (v20 default is 10254)
          "controller.service.annotations.service\\.beta\\.kubernetes\\.io/aws-load-balancer-healthcheck-port" = "80"

          # Keep client IP preservation (Elements' previous behaviour; live value today)
          "controller.service.annotations.service\\.beta\\.kubernetes\\.io/aws-load-balancer-target-group-attributes" = "preserve_client_ip.enabled=true"
        }
      }
```

Setting a value to `null` removes it; terraform-helm v20 filters out null values before passing them to Helm. Proxy protocol stays **off**, as v20 sets it, which matches your manual fix.

## What the plan and apply should do

- **ingress-nginx** is updated in place, and the Service loses port 61616.
- The controller can then reconcile cleanly. The target group should end up with proxy protocol **false**, preserve client IP **true**, and health check **HTTP 80 /healthz**, which is exactly what it has now. There should be no disruption.

Check after the apply:
```bash
kubectl -n ingress-control get svc ingress-nginx-controller          # only 443/TCP
aws elbv2 describe-target-group-attributes --target-group-arn $TG \
  --query "Attributes[?Key=='proxy_protocol_v2.enabled' || Key=='preserve_client_ip.enabled']" --output table
aws elbv2 describe-target-health --target-group-arn $TG \
  --query 'TargetHealthDescriptions[].[Target.Id,TargetHealth.State]' --output table
kubectl -n ingress-control logs deploy/aws-load-balancer-controller --since=15m --tail=-1 | grep -iE "error|failed"
```
Both targets should be healthy, and the controller log should have no errors.

## For the other environments

Every Elements environment you move to terraform-helm v20 will hit this same problem. Once dst is confirmed, move this `values` block into `eks-addons/env-config/common.tfvars` (blue and green) so all environments get it, and add it to the runbook.


