variable "environment" {
  type        = string
  description = "Deployment environment (dev, stage, prod)"
}

variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region"
}

variable "is_production_account" {
  type        = bool
  default     = false
  description = "Whether this is a production AWS account"
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
