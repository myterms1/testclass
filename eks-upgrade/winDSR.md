You run it **on the Windows node itself**, not in kubectl. The easiest way is AWS Systems Manager (SSM), with no RDP or password needed.

**Step 1: find the Windows node's instance ID**
```bash
kubectl get nodes -l kubernetes.io/os=windows \
  -o custom-columns=NAME:.metadata.name,ID:.spec.providerID
```
The ID looks like `aws:///us-east-1a/i-0abc123...`. You need the `i-...` part.

**Option A: interactive session (like SSH)**
```bash
aws ssm start-session --target i-0abc123...
```
Then, at the prompt:
```powershell
powershell
hnsdiag.exe list loadbalancers -d | Select-String IsDSR
```
(You need the Session Manager plugin installed for the AWS CLI. The AWS console also works: EC2 → select the instance → **Connect** → **Session Manager** tab.)

**Option B: run it without logging in**
```bash
CMD_ID=$(aws ssm send-command --instance-ids i-0abc123... \
  --document-name AWS-RunPowerShellScript \
  --parameters 'commands=["hnsdiag.exe list loadbalancers -d | Select-String IsDSR"]' \
  --query Command.CommandId --output text)

sleep 5
aws ssm get-command-invocation --command-id $CMD_ID --instance-id i-0abc123... \
  --query StandardOutputContent --output text
```

**What to expect:** several lines with `IsDSR : true` (or `"IsDSR": true`). If you see `false` or nothing at all, send me the output.

**If SSM doesn't connect**, the node may be missing the SSM agent or the instance role may lack `AmazonSSMManagedInstanceCore`. In that case, RDP through a bastion is the fallback. A debug pod on the node is also possible, but your Kyverno `restrict-image-registries` policy would likely block the Microsoft image, so SSM is the cleaner path.