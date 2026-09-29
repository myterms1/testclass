

File	Change
eks-cluster/env-config/us-east-1/dst.tfvars (or common.tfvars)	eks_version = "1.36"
eks-nodes/env-config/us-east-1/dst.tfvars (or common.tfvars)	eks_version = "1.36"
eks-addons/env-config/us-east-1/dst.tfvars	Cluster Autoscaler image.tag = "v1.36.1" (keep chart 9.59.0)

You don't need to change Kyverno (3.8.2 is already installed), WinDSR (already removed), the Terraform/Helm providers, or the module tags.