include {
  path = find_in_parent_folders()
}

terraform {
  extra_arguments "publish_vars" {
    commands = [
      "apply",
      "plan",
      "import",
      "push",
      "refresh",
      "output",
      "destroy"
    ]
    required_var_files = [
      "${get_parent_terragrunt_dir()}/common.tfvars",
      "${get_terragrunt_dir()}/env-config/common.tfvars",
      "${get_terragrunt_dir()}/env-config/${get_env(\"TF_VAR_region\", \"us-east-1\")}/common.tfvars",
      "${get_terragrunt_dir()}/env-config/${get_env(\"TF_VAR_region\", \"us-east-1\")}/${get_env(\"TF_VAR_env\", \"local\")}.tfvars"
    ]
  }
  after_hook "after_hook_plan" {
    commands = [
      "plan"
    ]
    execute = [
      "sh",
      "-c",
      "terraform show -json tf-plan.binary > ${get_terragrunt_dir()}/tf-plan.json"
    ]
  }
}
