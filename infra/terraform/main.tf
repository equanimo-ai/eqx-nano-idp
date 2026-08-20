module "nano_idp" {
  source = "./modules/nano-idp"

  environment   = var.environment
  name_prefix   = local.name_prefix
  image_tag     = var.image_tag
  cpu           = var.cpu
  memory        = var.memory
  desired_count              = var.desired_count
  domain_prefix              = var.domain_prefix
  enable_off_hours_schedule  = var.enable_off_hours_schedule
  schedule_start_cron        = var.schedule_start_cron
  schedule_stop_cron         = var.schedule_stop_cron
  schedule_timezone          = var.schedule_timezone
  common_tags                = local.common_tags
}
