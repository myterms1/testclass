resource "aws_glue_connection" "this" {
  name            = local.connection_name
  description     = var.glue_connection_description
  connection_type = upper(var.glue_connection_type)

  connection_properties = local.connection_properties_effective

  physical_connection_requirements {
    availability_zone      = coalesce(var.availability_zone, data.aws_subnet.glue_connection.availability_zone)
    security_group_id_list = local.glue_security_group_ids
    subnet_id              = local.selected_subnet_id
  }

  tags = local.tags
}
