vpc_id = data.terraform_remote_state.vpc.outputs.vpc_id

node_subnet_ids = flatten([for s in data.terraform_remote_state.vpc.outputs.additional_subnets : s.id])


data "aws_subnets" "pod_subnets" {
  filter {
    name   = "tag:Name"
    values = ["broker-apps-dev-non-routable-golden-subnet-*"]
  }
}

locals {
  pod_subnet_ids = data.aws_subnets.pod_subnets.ids
}


data "aws_subnets" "pod_subnets" {
  filter {
    name   = "vpc-id"
    values = [data.terraform_remote_state.vpc.outputs.vpc_id]  # Replace with your VPC ID reference
  }

  filter {
    name   = "tag:Name"
    values = ["broker-apps-dev-non-routable-golden-subnet-*"]
  }
}

locals {
  pod_subnet_ids = data.aws_subnets.pod_subnets.ids
}
