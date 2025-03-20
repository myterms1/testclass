vpc_id = data.terraform_remote_state.vpc.outputs.vpc_id

node_subnet_ids = flatten([for s in data.terraform_remote_state.vpc.outputs.additional_subnets : s.id])