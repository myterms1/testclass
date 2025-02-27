provider "aws" {
  region = "us-east-1" # Change this to your AWS region
}

# Define the environment variable
variable "env" {
  description = "Environment name (e.g., dev, prod, staging)"
  type        = string
  default     = "dev" # Change if needed
}

# Fetch VPC details (Replace with your actual VPC ID)
data "aws_vpc" "selected" {
  id = "vpc-xxxxxxxx" # Replace with your actual VPC ID
}

# Step 1: Create Private Hosted Zone only if var.env = "dev"
resource "aws_route53_zone" "private_hosted_zone" {
  count = var.env == "dev" ? 1 : 0  # Condition to create the resource only in dev
  name  = "xyz.io"

  vpc {
    vpc_id = data.aws_vpc.selected.id
  }

  comment = "Private hosted zone for xyz.io (Only in dev)"
}

# Step 2: Create A Record if the hosted zone exists
resource "aws_route53_record" "a_record" {
  count  = var.env == "dev" ? 1 : 0 # Create record only in dev
  zone_id = aws_route53_zone.private_hosted_zone[0].zone_id
  name    = "xyz.io"
  type    = "A"
  ttl     = 300
  records = ["10.0.1.100"] # Replace with your private IP
}

# Alternative: Create a CNAME Record if pointing to an Internal AWS Service
resource "aws_route53_record" "cname_record" {
  count  = var.env == "dev" ? 1 : 0 # Create record only in dev
  zone_id = aws_route53_zone.private_hosted_zone[0].zone_id
  name    = "xyz.io"
  type    = "CNAME"
  ttl     = 300
  records = ["internal-service.example.aws"] # Replace with actual internal service DNS
}
