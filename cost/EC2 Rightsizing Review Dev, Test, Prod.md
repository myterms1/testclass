# EC2 Rightsizing Review: Dev, Test, Prod

Oct 19, 2026 · @Expert1

## Executive summary

We can safely downsize 14 of the 29 ASGs FinOps flagged now, saving about **$1,232 per month**. Another 8 could save about **$664 per month** once we explain one CPU spike pattern. The remaining 7 must stay on r6i.xlarge.

FinOps claimed **$2,607 per month** from moving every ASG off r6i.xlarge. Their recommendation comes from AWS, which looks mainly at CPU. We checked 5 weeks of real CPU, memory and network data for every ASG. Three things change the picture:

- **Memory:** m7i-flex.large has 8 GiB, a quarter of today's 32 GiB. Most of our Windows servers peak at 6-7 GiB, so they would run at 80-92% memory. For those we recommend **r6i.large (16 GiB)** instead. It saves about 12% less, but runs at about 40-45% memory.
- **Network:** 6 ASGs push 0.77-2.1 Gbps at peak, more than any smaller size can sustain, so they stay as they are. A seventh (dev dst-facets-batch) stays because its CPU is genuinely busy, not just spiky.
- **CPU spikes:** Most servers are idle 95% of the time (p95 CPU of 3-7%) but spike to 60-75% once a week or more. With half the vCPUs, those spikes would max out the server. We need to know what causes them before downsizing.

| Environment | ASGs checked | FinOps claimed ($/mo) | Approve now | Approve after spike check | Keep r6i.xlarge | Savings now ($/mo) | Extra after spike check ($/mo) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Dev | 11 | 1,049 | 5 | 4 | 2 | 454 | 359 |
| Test | 8 | 539 | 3 | 2 | 3 | 203 | 105 |
| Prod | 10 | 1,018 | 6 | 2 | 2 | 575 | 200 |
| **Total** | **29** | **2,607** | **14** | **8** | **7** | **1,232** | **664** |

**Decision requested:** approve the 14 "approve now" changes (dev first, then test, then prod). Approve investigating the CPU spikes on the 8 "spike check" ASGs. Agree with FinOps that the 7 "keep" ASGs are not over-provisioned.

Savings for "approve now" and "spike check" use FinOps' own numbers where we accept their target. Where we propose r6i.large instead, the figure is about 88% of their number. Where we propose m7i-flex.large instead of c7i-flex.large, it is about 96%. That is based on approximate Windows on-demand list prices in us-east-1, and FinOps should confirm it.

## How we checked

We took the FinOps export and pulled CloudWatch data for every ASG in it. The data covers 4 full weeks plus part of a fifth (Sep 21 - Oct 19, 2026), in 5-minute samples, for three accounts: usmg-dev (851725216779), usmg-test (84828583690) and usmg-prod (971422678837). All 29 ASGs run Windows Server 2022 on r6i.xlarge (4 vCPU, 32 GiB).

| What we measured | Where it comes from | Why it matters |
| --- | --- | --- |
| CPU % (peak and p95) | AWS/EC2 CPUUtilization | Halving vCPUs doubles CPU %. The p95 shows normal busy load, and the peak shows the worst moment. |
| Memory % (peak and p95) | CloudWatch agent, "Memory % Committed Bytes In Use" | AWS's recommendation is mostly CPU-based. Cutting RAM from 32 to 8 GiB quadruples memory %. |
| Network (peak Mbps, busier of in/out) | AWS/EC2 NetworkIn / NetworkOut | Smaller sizes have a much lower sustained bandwidth (baseline). Traffic above it is slowed down. |
| Disk (peak MB/s and IOPS) | AWS/EC2 EBS metrics | Checked for completeness. It was not a limiting factor for any ASG. |

**Projection:** for each ASG we scaled today's usage onto the target size, as if the same work ran on the smaller server.

- **CPU on target** = CPU today × (4 vCPU ÷ target vCPU).
- **Memory on target** = memory today × (32 GiB ÷ target GiB).
- **Network on target** = peak Mbps ÷ the target's baseline bandwidth.

**Pass rules on the target size:**

- **Memory:** peak under 75%. Windows slows down and starts paging above this.
- **Network:** peak under 60% of baseline. Above 100% the server gets throttled.
- **CPU:** peak under 90% in prod, or 100% in dev/test.
- An ASG that passes memory and network but only fails the CPU peak (while its p95 stays low) is marked **spike check**, not rejected.

Newer instance types (m7i, r8i) are about 10-20% faster per vCPU than r6i. Our CPU projections ignore this, so they are slightly pessimistic, which is the safe direction.

## Why the AWS recommendation is not enough

AWS's tool flagged all 29 ASGs because their average CPU is very low, and that part is true. But average CPU is only one of three limits. Here is what the other two show, plus the CPU detail behind the average.

### 1. Memory: m7i-flex.large is too small for most of these servers

Apart from two outliers, our Windows servers peak at 2.7-7.4 GiB of memory, and most sit at 4-7 GiB. On 8 GiB, the busier ones would run at 78-92%, which leaves no room for patching, antivirus scans or a busy day. 14 of the 23 ASGs FinOps pointed at an 8 GiB size fail the 75% memory rule.

r6i.large keeps 16 GiB, so the same servers would sit at about 40-46%. It costs slightly more than m7i-flex.large, but still halves the vCPU count. On Windows the license is charged per vCPU, so most of the savings come from the vCPU cut either way.

### 2. Network: some servers move a lot of data

Smaller instances have a lower **baseline bandwidth**, meaning the speed they can sustain. They can burst above it for a while, then AWS throttles them.

| Size | Baseline bandwidth (approx.) |
| --- | --- |
| r6i.xlarge (today) | 1.56 Gbps |
| r6i.large | 0.78 Gbps |
| r8i-flex.large / m8i-flex.large | 0.47 Gbps |
| m7i-flex.large / c7i-flex.large | 0.39 Gbps |

Six ASGs peak between 769 and 2,142 Mbps. On every 2-vCPU size that is 98-550% of baseline, which means long transfers would be throttled. Three of them (test int-facets-task, prod prd-elements-batch, test pvs-facets-batch) already exceed even today's 1.56 Gbps at peak, so they are using their burst allowance now.

### 3. CPU: idle most of the time, with sharp spikes

For 24 of 29 ASGs, p95 CPU is between 3% and 15%, so the servers are mostly idle. But 16 of them peaked at 45-98% CPU at least once in the period. With half the vCPUs, a 70% spike becomes about 140%. The server would be maxed out and the work would take longer.

Whether that matters depends on what the spike is:

- **Harmless:** a new instance booting (Windows startup is CPU-heavy), Windows Update, an antivirus scan, or a deployment. A few slower minutes are fine.
- **Real work:** a batch job or a peak in user traffic. Running it on half the CPU makes it slower, which may be fine in dev but not in prod.

That is why those 8 ASGs need a spike check rather than a yes or no today.

### 4. Two test ASGs are already at their limits today

- **usmg-pvs-facets-batch-controller (test):** memory reached **99.6%** of committed memory, above 80% in 4 of 5 weeks. This server may need more memory, not less, or has a memory leak.
- **usmg-int-facets-task-controller (test):** CPU reached **97.6%** on today's 4 vCPUs, above 80% in 2 weeks.

Neither can be downsized. Both should be looked at by the application owner.

## Decision for every ASG

Each table is sorted by decision, then by savings. The CPU, memory and network columns show usage projected onto **our target** size. For "Keep" rows they show **FinOps' target** instead, to show why it fails. Savings are per ASG per month. Where our target differs from FinOps', the figure is an estimate (see the executive summary).

### Dev (usmg-dev, 851725216779)

| ASG | FinOps target (claimed $/mo) | Decision | Our target | CPU peak / p95 on target | Memory peak on target | Network peak, Mbps (% of target baseline) | Our savings ($/mo) | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cdv-facets-batch | m7i-flex.large (97) | Approve as recommended | m7i-flex.large | 81% / 13% | 72% | 21 (5%) | 97 | Fits: CPU peak 81%, memory 72%, network 5%. Memory is close to the line, so watch it for 2 weeks after the change. |
| cdv-elements-batch | m7i-flex.large (95) | Approve as recommended | m7i-flex.large | 57% / 7% | 47% | 16 (4%) | 95 | All three limits fit: CPU peak 57%, memory 47%, network 4%. |
| dev-elements-batch | m7i-flex.large (106) | Approve r6i.large instead | r6i.large | 95% / 11% | 42% | 35 (4%) | 93 | m7i-flex.large would reach 84% memory. r6i.large: memory 42%, CPU peak 95% with p95 11%, which is acceptable for dev. |
| cdv-elements-task | m7i-flex.large (104) | Approve r6i.large instead | r6i.large | 67% / 8% | 42% | 40 (5%) | 91 | m7i-flex.large would reach 83% memory. r6i.large: CPU peak 67%, memory 42%, network 5%. |
| cdv-facets-task | m7i-flex.large (88) | Approve r6i.large instead | r6i.large | 88% / 9% | 39% | 49 (6%) | 78 | m7i-flex.large would reach 79% memory. r6i.large keeps memory at 39% and CPU peaks at 88%, which is acceptable for dev. |
| dst-elements-batch | m7i-flex.large (94) | Spike check first | m7i-flex.large | 142% / 8% | 55% | 50 (13%) | 94 (pending) | Memory (55%) and network fit m7i-flex.large. CPU is idle (p95 8%) but spikes to 142%. Find the spike cause, then approve. |
| dev-elements-task | m7i-flex.large (106) | Spike check first | r6i.large | 146% / 8% | 41% | 59 (8%) | 93 (pending) | m7i-flex.large would reach 82% memory, so not that size. On r6i.large memory (41%) fits, but CPU spikes to 146%. |
| dev-facets-task | m7i-flex.large (103) | Spike check first | r6i.large | 116% / 10% | 41% | 373 (48%) | 91 (pending) | Network (373 Mbps) is 96% of m7i-flex.large baseline, so not that size. On r6i.large, network (48%) and memory (41%) fit, but CPU spikes to 116%. |
| dst-elements-task | r6i.large (81) | Spike check first | r6i.large | 131% / 8% | 59% | 171 (22%) | 81 (pending) | Memory (59%) and network (22%) fit r6i.large. CPU is idle (p95 8% on target) but spikes to 131%. Find the spike cause, then approve. |
| dev-facets-batch | r8i-flex.large (72) | Keep r6i.xlarge | r6i.xlarge (no change) | 129% / 31% | 154% | 1,121 (240%) | 0 | Network peaks at 1,121 Mbps, 240% of r8i-flex.large baseline and 144% even on r6i.large. Memory also spiked to 77% of 32 GiB (about 25 GiB), which would not fit in 16 GiB. |
| dst-facets-batch | m7i-flex.large (103) | Keep r6i.xlarge | r6i.xlarge (no change) | 138% / 63% | 58% | 22 (6%) | 0 | The only dev ASG with real sustained CPU: p95 31% today, 63% on 2 vCPU, peaks at 138%. Flex sizes are not meant for sustained load. |

Dev: **$454/mo** approved now, **$359/mo** more after the spike check.

### Test (usmg-test, 84828583690)

| ASG | FinOps target (claimed $/mo) | Decision | Our target | CPU peak / p95 on target | Memory peak on target | Network peak, Mbps (% of target baseline) | Our savings ($/mo) | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pvs-elements-task | m7i-flex.large (81) | Approve r6i.large instead | r6i.large | 60% / 14% | 44% | 78 (10%) | 71 | m7i-flex.large would reach 87% memory. r6i.large: CPU peak 60%, memory 44%, network 10%. |
| pvs-elements-batch | m7i-flex.large (78) | Approve r6i.large instead | r6i.large | 50% / 11% | 39% | 58 (7%) | 68 | m7i-flex.large would reach 78% memory. r6i.large: CPU peak 50%, memory 39%, network 7%. |
| int-elements-task | m7i-flex.large (73) | Approve r6i.large instead | r6i.large | 61% / 12% | 46% | 68 (9%) | 64 | m7i-flex.large would reach 92% memory. r6i.large: CPU peak 61%, memory 46%, network 9%. |
| int-elements-batch | m7i-flex.large (65) | Spike check first | r6i.large | 154% / 42% | 44% | 203 (26%) | 57 (pending) | m7i-flex.large would reach 87% memory. On r6i.large memory (44%) and network (26%) fit, and CPU p95 is 42%, but peaks reach 154%. |
| pvs-facets-task | r6i.large (48) | Spike check first | r6i.large | 147% / 29% | 68% | 143 (18%) | 48 (pending) | Memory (68%) and network (18%) fit r6i.large. CPU p95 is 29% on target, but peaks reach 147%. Find the spike cause first. |
| pvs-facets-batch | r8i-flex.large (56) | Keep r6i.xlarge | r6i.xlarge (no change) | 155% / 42% | 199% | 1,777 (380%) | 0 | Already at its limits: memory reached 99.6% of committed memory (above 80% in 4 weeks) and network peaks at 1,777 Mbps. Needs investigation, not a downsize. |
| int-facets-task | m7i-flex.large (61) | Keep r6i.xlarge | r6i.xlarge (no change) | 195% / 12% | 86% | 2,120 (544%) | 0 | CPU already hits 98% on 4 vCPU today (above 80% in 2 weeks). Network peaks at 2,120 Mbps, 5x the m7i-flex.large baseline. |
| int-facets-batch | m8i-flex.large (77) | Keep r6i.xlarge | r6i.xlarge (no change) | 148% / 40% | 86% | 1,313 (280%) | 0 | Network peaks at 1,313 Mbps, 280% of m8i-flex.large baseline and 168% of r6i.large. CPU p95 is also 20% today. |

Test: **$203/mo** approved now, **$105/mo** more after the spike check.

### Prod (usmg-prod, 971422678837)

| ASG | FinOps target (claimed $/mo) | Decision | Our target | CPU peak / p95 on target | Memory peak on target | Network peak, Mbps (% of target baseline) | Our savings ($/mo) | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pfx-elements-task | m7i-flex.large (105) | Approve as recommended | m7i-flex.large | 54% / 6% | 46% | 15 (4%) | 105 | All three limits fit: CPU peak 54%, memory 46%, network 4%. |
| prd-facets-task | r6i.large (81) | Approve as recommended | r6i.large | 77% / 7% | 60% | 83 (11%) | 81 | All three limits fit: CPU peak 77%, memory 60%, network 11%. |
| pfx-elements-batch | c7i-flex.large (114) | Approve m7i-flex.large instead | m7i-flex.large | 56% / 6% | 34% | 16 (4%) | 110 | c7i-flex.large has only 4 GiB, so memory would be 68%, too tight for Windows Server in prod. m7i-flex.large gives 34% memory for about $5/mo less savings. |
| rel-elements-task | m7i-flex.large (106) | Approve r6i.large instead | r6i.large | 65% / 11% | 42% | 79 (10%) | 93 | m7i-flex.large would reach 85% memory. r6i.large: CPU peak 65%, memory 42%, network 10%. |
| pfx-facets-task | m7i-flex.large (106) | Approve r6i.large instead | r6i.large | 66% / 11% | 44% | 12 (2%) | 93 | m7i-flex.large would reach 88% memory. r6i.large: CPU peak 66%, memory 44%, network 2%. |
| prd-elements-task | m7i-flex.large (106) | Approve r6i.large instead | r6i.large | 56% / 7% | 40% | 41 (5%) | 93 | m7i-flex.large would reach 80% memory. r6i.large: CPU peak 56%, memory 40%, network 5%. |
| pfx-facets-batch | m7i-flex.large (106) | Spike check first | m7i-flex.large | 94% / 13% | 65% | 22 (6%) | 106 (pending) | Memory (65%) and network (6%) fit, but CPU peaks at 94%, above the 90% prod limit. Confirm the spike is harmless, then approve. |
| rel-elements-batch | m7i-flex.large (106) | Spike check first | r6i.large | 127% / 7% | 28% | 225 (29%) | 94 (pending) | Network is 58% of m7i-flex.large baseline (too close), but only 29% on r6i.large. Memory fits (28%), but CPU spikes to 127%. |
| rel-facets-task | r6i.large (81) | Keep r6i.xlarge | r6i.xlarge (no change) | 123% / 14% | 53% | 769 (98%) | 0 | Network peaks at 769 Mbps, 98% of r6i.large baseline, so it would be throttled. CPU would also spike to 123%. |
| prd-elements-batch | m7i-flex.large (107) | Keep r6i.xlarge | r6i.xlarge (no change) | 134% / 7% | 65% | 2,142 (549%) | 0 | Network peaks at 2,142 Mbps, 5.5x the m7i-flex.large baseline and above even today's 1.56 Gbps. |

Prod: **$575/mo** approved now, **$200/mo** more after the spike check.

## Required actions

Roll out in three waves: dev first, then test, then prod. Each wave waits one clean week after the one before it. Run the spike checks in parallel, so those 8 ASGs can join a later wave.

### Before any change

- [ ] **Check Reserved Instances and Savings Plans with FinOps.** Windows Reserved Instances are not size-flexible. If an r6i.xlarge RI covers these servers, downsizing leaves the RI unused and saves nothing until it expires. A Compute Savings Plan does not have this problem.
- [ ] **Send FinOps this document.** Agree on the r6i.large alternative for the memory-bound ASGs, and ask them to re-price the 14 rows where our target differs from theirs.
- [ ] **Create two CloudWatch alarms per ASG you change.** One for memory ("Memory % Committed Bytes In Use" above 85% for 15 minutes), one for CPU (CPUUtilization average above 90% for 15 minutes). These tell you quickly if a downsize was too far.

### Wave 1: dev (week 1), 5 ASGs, about $454/mo

- [ ] cdv-facets-batch to m7i-flex.large
- [ ] cdv-elements-batch to m7i-flex.large
- [ ] dev-elements-batch to r6i.large
- [ ] cdv-elements-task to r6i.large
- [ ] cdv-facets-task to r6i.large

### Wave 2: test (week 2), 3 ASGs, about $203/mo

- [ ] pvs-elements-task to r6i.large
- [ ] pvs-elements-batch to r6i.large
- [ ] int-elements-task to r6i.large

### Wave 3: prod (weeks 3-4, in a change window), 6 ASGs, about $575/mo

- [ ] pfx-elements-task to m7i-flex.large
- [ ] prd-facets-task to r6i.large
- [ ] pfx-elements-batch to m7i-flex.large (not c7i-flex.large)
- [ ] rel-elements-task to r6i.large
- [ ] pfx-facets-task to r6i.large
- [ ] prd-elements-task to r6i.large

### How to change one ASG

1. **Create a new launch template version.** Copy the current version and change only the instance type. Note the old version number, because that is your rollback.
2. **Point the ASG at the new version.** If the ASG uses a mixed instances policy, change the instance type in its overrides instead.
3. **Start an instance refresh** with minimum healthy percentage 90% and a warm-up long enough for Windows to boot and the app to start (usually 10-15 minutes). One instance is replaced at a time, so the service stays up.
4. **Watch it for 30 minutes.** Check that new instances pass health checks and the application responds.
5. **Watch it for 2 weeks.** Keep an eye on the alarms, then re-run the script for that account with `--weeks 2` to confirm peaks on the new size.
6. **Rollback if needed.** Point the ASG back at the old launch template version and start another instance refresh. It takes the same time as the change.

### Spike check: 8 ASGs, about $664/mo

The goal is to find out what causes each CPU spike.

1. In CloudWatch, open **Metrics, then EC2, then By Auto Scaling Group, then CPUUtilization** for the ASG.
2. Set the statistic to **Maximum**, the period to **5 minutes** and the range to **4 weeks**. Note the date and time of each spike.
3. Compare those times with:
   - **The ASG's Activity history:** a spike right after an instance launch is Windows booting.
   - **The patch window** (SSM Patch Manager or WSUS).
   - **The antivirus scan schedule.**
   - **Deployments and batch job schedules.**
4. Decide:
   - Boot, patching, antivirus or a deployment means the spike is harmless. Approve the target in the table.
   - A real batch job or user peak in dev/test: approve if the team accepts that the job will run slower.
   - A real batch job or user peak in prod: keep r6i.xlarge.

- [ ] Dev: dst-elements-batch, dev-elements-task, dev-facets-task, dst-elements-task
- [ ] Test: int-elements-batch, pvs-facets-task
- [ ] Prod: pfx-facets-batch, rel-elements-batch

### Keep r6i.xlarge: 7 ASGs, no change

- [ ] **Tell FinOps these 7 are reviewed and should stay on r6i.xlarge.** The reasons are network throughput (6 ASGs) or sustained CPU (dev dst-facets-batch). The data is in the tables above.
- [ ] **Ask the app owner to investigate test pvs-facets-batch.** Memory reaches 99.6% of committed memory. Check for a memory leak or a page file that is too small.
- [ ] **Ask the app owner to investigate test int-facets-task.** CPU reaches 98% on today's 4 vCPUs.
- [ ] **Re-check all 7 in 3 months,** or after a major release changes their load.

## Glossary

| Term | Meaning |
| --- | --- |
| ASG | Auto Scaling Group: a set of identical EC2 instances that AWS keeps running. Resizing it means changing the instance type in its launch template. |
| Peak | The highest 5-minute value in the period, on the busiest instance in the ASG. |
| p95 | 95% of the time, usage was at or below this value. It shows the normal busy level, ignoring rare spikes. |
| On target | Today's usage projected onto the smaller size. Over 100% means the smaller server would be maxed out. |
| Committed memory | Windows' measure of memory in use, including what is reserved in the page file. It is a cautious (slightly high) measure of RAM use. |
| Baseline bandwidth | The network speed an instance can sustain. Smaller sizes can burst above it for a while, then are throttled back to it. |
| Flex instances (m7i-flex, r8i-flex, c7i-flex) | Cheaper sizes that give full CPU most of the time but are not meant for constant 100% CPU. |
| Spike check | A look at when CPU spikes happen, to tell harmless spikes (boot, patching, antivirus) from real workload. |

Data: CloudWatch, Sep 21 - Oct 19, 2026, collected with the rightsizing\_check.py script from the FinOps "usmg-cost-saving-opportunities" export. Instance sizes and bandwidth come from the AWS EC2 API. Price ratios for the alternative sizes are approximate on-demand Windows list prices for us-east-1.
