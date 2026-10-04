
**Step 1: find where the two branches split**
```bash
cd gsm-terraform-helm          # repeat for gsm-eks-addons
git fetch --all
MB=$(git merge-base origin/main origin/upgrades)
git log -1 --format='%h %ad %s' --date=short $MB
```
`merge-base` gives the last commit both branches share. Here it was 19 June 2025.

**Step 2: count how far each branch moved since then**
```bash
git rev-list --count $MB..origin/main
git rev-list --count $MB..origin/upgrades
```

**Step 3: see what kind of work went on each branch**
```bash
# only on main
git log --no-merges --format='%ad %an | %s' --date=short $MB..origin/main
# only on upgrades, oldest first
git log --no-merges --reverse --format='%ad %an | %s' --date=short $MB..origin/upgrades
# who did the work
git log --no-merges --format='%an' $MB..origin/upgrades | sort | uniq -c
```
The commit messages showed the pattern: "Removed kube-prometheus-stack" and "Container Insights" on upgrades, Superset changes on main.

**Step 4: compare which charts exist on each branch**
```bash
git show origin/main:locals.tf     | grep -oE '^    "?[a-z0-9-]+"? *= *\{' | tr -d ' ={"' | sort -u > /tmp/main.txt
git show origin/upgrades:locals.tf | grep -oE '^    "?[a-z0-9-]+"? *= *\{' | tr -d ' ={"' | sort -u > /tmp/upg.txt
comm -23 /tmp/main.txt /tmp/upg.txt   # charts only on main (removed in upgrades)
comm -13 /tmp/main.txt /tmp/upg.txt   # charts only on upgrades (new)
```
`git show branch:file` reads a file from a branch without checking it out.

**Step 5: see what eks-apps deploys**
```bash
cd gsm-metal
grep -n "ref=" module/aws/eks-apps/*.tf
grep -oE '^\s{4,8}"?[a-z0-9-]+"? *= *\{' module/aws/eks-apps/env-config/common.tfvars | tr -d ' ={"' | sort -u
```
This showed superset, tcs-api, tcs-ui, workflow and metal-utils. They're all app charts, which explains why eks-apps stayed on main.

**Step 6: trial merge in a throwaway copy (safe, touches nothing real)**
```bash
cd /tmp && git clone <your-local-path>/gsm-terraform-helm trial && cd trial
git checkout -b upgrades origin/upgrades
git checkout main
git merge --no-commit --no-ff upgrades     # try the merge, don't commit
git diff --cached --stat | tail -1         # size of the change
git merge --abort                          # undo
```
The `CONFLICT` lines in the output are the files you'd need to fix by hand.
