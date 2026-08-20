variable "environment" {
  type = string
}

variable "name_prefix" {
  type    = string
  default = "eqx-nano-idp"
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "cpu" {
  type    = number
  default = 256
}

variable "memory" {
  type    = number
  default = 512
}

variable "desired_count" {
  type    = number
  default = 1
}


variable "domain_prefix" {
  type    = string
  default = "idp"
}

variable "enable_off_hours_schedule" {
  type        = bool
  default     = true
  description = "Enable EventBridge Scheduler start/stop schedule for business hours"
}

variable "schedule_start_cron" {
  type        = string
  default     = "cron(0 9 * * ? *)"
  description = "Cron expression for starting service (default 09:00 AM ET)"
}

variable "schedule_stop_cron" {
  type        = string
  default     = "cron(0 0 * * ? *)"
  description = "Cron expression for stopping service (default 12:00 AM / Midnight ET)"
}

variable "schedule_timezone" {
  type        = string
  default     = "America/New_York"
  description = "Timezone for EventBridge Scheduler"
}

variable "common_tags" {
  type    = map(string)
  default = {}
}

