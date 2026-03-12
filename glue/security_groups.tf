resource "aws_security_group" "glue" {
  count       = var.create_glue_security_group ? 1 : 0
  name        = local.sg_name
  description = "Security group for ${local.job_name}"
  vpc_id      = local.vpc_id

  dynamic "egress" {
    for_each = toset(var.allowed_https_cidrs)
    content {
      description = "Allow outbound HTTPS"
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = [egress.value]
    }
  }

  dynamic "egress" {
    for_each = toset(var.internal_egress_ports)
    content {
      description = "Allow internal outbound TCP ${egress.value}"
      from_port   = egress.value
      to_port     = egress.value
      protocol    = "tcp"
      cidr_blocks = local.internal_egress_cidrs_effective
    }
  }

  tags = local.tags
}

locals {
  glue_security_group_ids = concat(
    var.create_glue_security_group ? [aws_security_group.glue[0].id] : [],
    var.security_group_ids
  )
}
