import re

# File paths (update these to your local paths)
file_a_path = "FileAK.tf"
file_b_path = "FileBK.tf"

# Read both files
with open(file_a_path, 'r') as file_a:
    content_a = file_a.read()

with open(file_b_path, 'r') as file_b:
    content_b = file_b.read()

# Regex pattern to extract ARNs
arn_pattern = r"arn:aws:[\w\-:/]+"

# Extract ARNs from both files
arns_a = set(re.findall(arn_pattern, content_a))
arns_b = set(re.findall(arn_pattern, content_b))

# Find ARNs present in A but missing in B
missing_arns_in_b = sorted(arns_a - arns_b)

# Output the result
if missing_arns_in_b:
    print("ARNs present in FileAK.tf but missing in FileBK.tf:\n")
    for arn in missing_arns_in_b:
        print(arn)
else:
    print("No ARNs are missing in FileBK.tf.")
