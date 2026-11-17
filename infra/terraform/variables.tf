variable "environment" {
  type        = string
  description = "Deployment environment (dev, prod)"
}

variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region"
}
