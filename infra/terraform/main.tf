module "nano_idp" {
  source = "./modules/nano-idp"

  environment           = var.environment
  name_prefix           = local.name_prefix
  image_tag             = var.image_tag
  cpu                   = var.cpu
  memory                = var.memory
  desired_count         = var.desired_count
  is_production_account = var.is_production_account
  domain_prefix         = var.domain_prefix
  common_tags           = local.common_tags
}
