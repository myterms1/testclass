Think of ingress-nginx as the **front door** of the cluster. Every request from outside comes in through it, and it decides which app gets the request.

**The request path**

```
flowchart LR
    U["User / browser"] --> DNS["Route53 DNS name"]
    DNS --> NLB["AWS NLB - internal<br/>port 443, TLS with ACM cert"]
    NLB -->|"re-encrypted TLS"| NGX["ingress-nginx pods<br/>namespace ingress-control"]
    NGX -->|"Ingress rules: host / path"| SVC["App Service"]
    SVC --> POD["App pods"]
```

(Paste into the **Code** tab on mermaid.live.)

Here's your block, section by section.

**1. Basics**
- `enabled = false`: the chart is off by default. Each repo (metal, tacets) turns it on in its own tfvars.
- The chart version is `4.14.0`, installed in the `ingress-control` namespace.
- `ingressClassResource.default = true`: any Ingress without a class uses this nginx.

**2. Size and scaling**
- Each pod requests 100m CPU and 1Gi memory.
- Autoscaling keeps at least **2 pods** and adds more above 85% CPU or memory.
- `topologySpreadConstraints` spreads the pods across **zones** and **nodes**, so one failure doesn't take down the front door.

**3. Creating the AWS load balancer**
These are annotations on the Kubernetes Service. The **AWS Load Balancer Controller** reads them and builds the NLB:
- `type = external`: the AWS LB Controller handles it, not the old built-in Kubernetes one.
- `nlb-target-type = ip`: the NLB sends traffic **directly to pod IPs**, not to nodes.
- `scheme = internal`: private, reachable only inside the network.
- `subnets`: which subnets the NLB lives in.

**4. Client IP and health checks (the part that caused your outage)**
- **Proxy protocol** is a small header the NLB adds to each connection that says "the real client IP is X". **Both sides must agree.** If the NLB sends it and nginx doesn't expect it (or the other way round), every request breaks. That was your outage: nginx was set to `false`, but the target group was still `true`.
- `preserve_client_ip`: another way to keep the real client IP. tacets turned it off for ActiveMQ.
- Health check: the NLB asks each pod "are you alive?" over HTTP at port 10254, path `/healthz`. If a pod doesn't answer, the NLB stops sending it traffic.

**5. Load balancer attributes**
- These turn on deletion protection and cross-zone load balancing.
- As noted before, the comma in the value isn't escaped, so Helm splits it and cross-zone isn't actually applied.

**6. TLS (encryption)**
- `ssl-ports = 443` plus the ACM cert: the NLB decrypts HTTPS using the AWS cert.
- `backend-protocol = ssl`: the NLB **re-encrypts** traffic to nginx, so it's encrypted end to end.
- `default-ssl-certificate`: the cert nginx itself uses, from a Kubernetes secret.
- `enableHttp = false`: only port 443, no plain HTTP.
- The TLS policy allows only TLS 1.2 and 1.3.

**7. The pricer part (tacets only)**
- Normally nginx handles **HTTP** traffic. It can also forward **raw TCP** traffic, which is what the `tcp.*` setting does.
- `tcp.61616 = batch/pricer-networx:61616`: anything arriving on port 61616 goes to the pricer service's ActiveMQ in the `batch` namespace.
- `ports.pricer = 61616`: opens port 61616 on the Service, and therefore on the NLB.
- metal has no `pricer-networx` service, which is why you set both to `null`.
- The last line (`proxy_protocol_v2.enabled`) isn't a real AWS annotation. It does nothing.

**In one line:** the NLB is the outer gate (AWS, TLS, health checks), nginx is the inner receptionist (routes by hostname and path), and the annotations are the instructions that tell AWS how to build the gate.