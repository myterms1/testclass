resource "null_resource" "install_kubectl" {
  provisioner "local-exec" {
    command = <<EOT
      curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
      chmod +x kubectl
      sudo mv kubectl /usr/local/bin/
      kubectl version --client
    EOT
  }
}

resource "null_resource" "validate_kubectl" {
  depends_on = [null_resource.install_kubectl]

  provisioner "local-exec" {
    command = <<EOT
      if ! command -v kubectl &> /dev/null; then
        echo "ERROR - could not execute kubectl version --client; you must have a kubectl binary installed!"
        exit 1
      else
        kubectl version --client
      fi
    EOT
  }
}







resource "null_resource" "validate_kubectl" {
  triggers = {
    id = timestamp()
  }

  provisioner "local-exec" {
    command = <<EOT
    if ! command -v kubectl &> /dev/null; then
      echo "ERROR - could not execute kubectl version --client; you must have a kubectl binary installed!"
      exit 1
    fi
    EOT
  }
}












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
