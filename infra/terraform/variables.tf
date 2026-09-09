variable "environment" {
  type        = string
  description = "Deployment environment (dev, stage, prod)"
}

variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region"
}


variable "image_tag" {
  type        = string
  default     = "latest"
  description = "Docker image tag for NanoIDP container"
}

variable "cpu" {
  type        = number
  default     = 256
  description = "ECS Task CPU units (256 = 0.25 vCPU)"
}

variable "memory" {
  type        = number
  default     = 512
  description = "ECS Task Memory in MB (512 MB)"
}

variable "desired_count" {
  type        = number
  default     = 1
  description = "Desired number of running ECS tasks"
}

variable "domain_prefix" {
  type        = string
  default     = "idp"
  description = "Subdomain prefix for NanoIDP (e.g. idp.dev.equanimo.io)"
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

variable "capacity_provider_strategy" {
  type = list(object({
    capacity_provider = string
    weight            = number
    base              = optional(number, 0)
  }))
  default     = [{ capacity_provider = "FARGATE", weight = 100 }]
  description = "On-demand by default; dev sets FARGATE_SPOT in envs/dev/dev.tfvars."
}
