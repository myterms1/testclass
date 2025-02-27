provider "aws" {
  region = "us-east-1" # Update based on your AWS region
}

variable "env" {
  description = "Deployment environment (e.g., dev, dev2, int)"
  type        = string
  default     = "dev"
}

# Local map to store VPC IDs
locals {
  vpc_ids = {
    dev  = "vpc-0a1c8a"
    qa = "vpc-04ad"
    prod  = "vpc-0e0808"
  }
  vpc_id = local.vpc_ids[var.env]
}

# Fetch VPC details
data "aws_vpc" "selected" {
  id = local.vpc_id
}

# Fetch the VPC Endpoint for SQS dynamically using VPC ID
data "aws_vpc_endpoint" "sqs_endpoint" {
  filter {
    name   = "vpc-id"
    values = [local.vpc_id]
  }

  filter {
    name   = "service-name"
    values = ["com.amazonaws.us-east-1.sqs"]
  }
}

# Fetch the ECS Security Group dynamically using a tag-based search
data "aws_security_group" "ecs_sg" {
  filter {
    name   = "tag:Role"
    values = ["ECS"]
  }
  filter {
    name   = "tag:Environment"
    values = [var.env]
  }
  vpc_id = local.vpc_id
}
######################################################################################


# Allow ECS to send HTTPS (443) traffic to the SQS VPC Endpoint
resource "aws_security_group_rule" "ecs_allow_sqs_endpoint" {
  type                     = "egress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = data.aws_security_group.ecs_sg.id
  description              = "Allow ECS tasks to communicate with SQS VPC Endpoint"
  source_security_group_id = data.aws_vpc_endpoint.sqs_endpoint.security_group_ids[0]
}

# Allow the SQS VPC Endpoint to receive HTTPS (443) traffic from ECS
resource "aws_security_group_rule" "sqs_endpoint_allow_ecs" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = data.aws_vpc_endpoint.sqs_endpoint.security_group_ids[0]
  description              = "Allow incoming traffic from ECS to SQS VPC Endpoint"
  source_security_group_id = data.aws_security_group.ecs_sg.id
}








