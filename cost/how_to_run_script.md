Here's the whole thing in plain steps. You run it on your Mac (the one with the Excel sheet).

**Step 1: Put both files in one folder**
- Make a folder, for example `rightsizing` on your Desktop.
- Download **rightsizing_check.py** from this chat into it.
- Put the FinOps Excel file in the same folder, and rename it to `finops.xlsx` to keep it short.

**Step 2: Open Terminal in that folder**
- Open the **Terminal** app.
- Type `cd ~/Desktop/rightsizing` and press Enter.

**Step 3: Install what the script needs (one time only)**
```
pip3 install boto3 pandas openpyxl
```

**Step 4: Check your AWS logins**
```
cat ~/.aws/config
```
You'll see names like `[profile usmg-dev]`, one for each account. If you sign in with SSO, run `aws sso login --profile usmg-dev` first.

**Step 5: Run the script**
Pair each account number with its profile name:
```
python3 rightsizing_check.py finops.xlsx --profile-map 111222333444=usmg-dev
```
- For more accounts, add more pairs on the same line, for example `222233334444=usmg-qa`.
- It prints progress for each server and takes a few minutes.

**Step 6: Open the result**
A new file named something like `rightsizing_check_2026-10-14.xlsx` appears in the folder. Open the **Summary** tab and look at the **verdict** column:
- 🟢 **SAFE TO DOWNSIZE**: agree with FinOps.
- 🟡 **BORDERLINE**: tight fit, discuss before changing.
- 🔴 **KEEP CURRENT**: the smaller size would run out of CPU or memory.
- 🟠 **NEED MEMORY DATA**: AWS isn't measuring memory on that server, so nobody knows yet.

**Step 7: If you see "NEED MEMORY DATA"**
- Install the CloudWatch agent on those Windows servers.
- Wait 2–4 weeks for data to build up.
- Run Step 5 again.

**Step 8: Present it**
Show the Summary tab to your manager or FinOps. The **Weekly** tab has the week-by-week proof.

If any step gives an error, paste the message here and I'll tell you the fix.


======================================================================================================================

There is **only one script**: `rightsizing_check.py`. You run it **once**, it finishes on its own in a few minutes, and then it's done. You do **not** leave it running for a week.

**Why it doesn't need to run for a week:** AWS has already been recording CPU, network and disk for your servers every 5 minutes. That history is stored in CloudWatch. The script just reads the **last 4 weeks** of that saved history, all at once, and puts it into Excel.

**The full flow, start to finish:**

**1. Today, about 10 minutes**
- Download `rightsizing_check.py` from this chat.
- Put it in one folder with your FinOps Excel file, renamed to `finops.xlsx`.
- Open Terminal and go to that folder: `cd ~/Desktop/rightsizing`
- Install the helpers, one time only: `pip3 install boto3 pandas openpyxl`

**2. Today, run the script once (about 2–10 minutes)**
```
python3 rightsizing_check.py finops.xlsx --profile-map 111222333444=usmg-dev
```
- While it runs you'll see lines like `[3/11] 111222333444 us-east-1 usmg-dst-...`, one per server.
- When it prints **"Wrote rightsizing_check_2026-10-14.xlsx"**, it's finished and has stopped by itself.

**3. Today, open the new Excel file**
- Check the **verdict** column on the Summary tab.
- Rows marked SAFE, BORDERLINE or KEEP: you're done. Use these in your meeting.
- Rows marked **NEED MEMORY DATA**: go to step 4.

**4. Only if you got "NEED MEMORY DATA"**
- AWS doesn't record memory by default. It needs the CloudWatch agent installed on the Windows servers.
- Install the agent on those servers. This is a one-time setup, not the script.
- Wait **2–4 weeks**, so memory history builds up.

**5. After 2–4 weeks, run the same script again**
- Use the exact same command as step 2.
- It finishes in minutes again, and now memory is included.

**In short:** run the script today, read the Excel, and run it again in a few weeks only if memory data was missing.
