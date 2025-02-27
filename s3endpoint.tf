provider "aws" {
  region = "us-east-1" # Change this to your AWS region
}

# Define environment variable (dev, staging, prod)
variable "env" {
  description = "Deployment environment (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"
}

# Map for VPC IDs based on environment
locals {
  vpc_ids = {
    dev  = "vpc-0a1c8a"
    qa = "vpc-04ad"
    prod  = "vpc-0e0808"
  }
  vpc_id = local.vpc_ids[var.env]
}

# Fetch the correct VPC
data "aws_vpc" "selected" {
  id = local.vpc_id
}

# Create an S3 VPC Endpoint (if not already created)
resource "aws_vpc_endpoint" "s3_endpoint" {
  vpc_id       = local.vpc_id
  service_name = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway" # S3 uses a Gateway endpoint
  route_table_ids = ["rtb-xxxxxxxx"] # Replace with your Route Table ID
}

# Create a Security Group for S3 VPC Endpoint
resource "aws_security_group" "s3_vpce_sg" {
  vpc_id = local.vpc_id
  name   = "s3-vpc-endpoint-sg"
  description = "Allow traffic from ECS to S3 VPC Endpoint"
}

# Allow ECS to send traffic to S3 VPC Endpoint (Egress Rule)
resource "aws_security_group_rule" "ecs_allow_s3_endpoint" {
  type                     = "egress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = data.aws_security_group.ecs_sg.id
  source_security_group_id = aws_security_group.s3_vpce_sg.id
  description              = "Allow ECS tasks to communicate with S3 via VPC Endpoint"
}

# Allow inbound traffic from ECS to S3 VPC Endpoint
resource "aws_security_group_rule" "s3_vpce_allow_ecs" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.s3_vpce_sg.id
  source_security_group_id = data.aws_security_group.ecs_sg.id
  description              = "Allow incoming traffic from ECS to S3 VPC Endpoint"
}

# Fetch ECS Security Group dynamically (Ensure your ECS tasks are tagged correctly)
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

# Create an S3 bucket
resource "aws_s3_bucket" "my_bucket" {
  bucket = "my-private-bucket-${var.env}" # Change to your actual S3 bucket name
}

# Restrict S3 access only via VPC Endpoint
resource "aws_s3_bucket_policy" "restrict_s3_to_vpc_endpoint" {
  bucket = aws_s3_bucket.my_bucket.id
  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Deny",
            "Principal": "*",
            "Action": "s3:*",
            "Resource": [
                "arn:aws:s3:::${aws_s3_bucket.my_bucket.id}",
                "arn:aws:s3:::${aws_s3_bucket.my_bucket.id}/*"
            ],
            "Condition": {
                "StringNotEquals": {
                    "aws:SourceVpce": "${aws_vpc_endpoint.s3_endpoint.id}"
                }
            }
        }
    ]
}
POLICY
}
