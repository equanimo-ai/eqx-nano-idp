output "ecr_repository_url" {
  value       = module.nano_idp.ecr_repository_url
  description = "ECR repository URL for NanoIDP container images"
}

output "config_bucket_name" {
  value       = module.nano_idp.config_bucket_name
  description = "S3 bucket managing NanoIDP configuration"
}

output "config_bucket_arn" {
  value       = module.nano_idp.config_bucket_arn
  description = "ARN of S3 configuration bucket"
}

output "issuer_url" {
  value       = module.nano_idp.issuer_url
  description = "Public OIDC Issuer URL for NanoIDP"
}

output "fqdn" {
  value       = module.nano_idp.fqdn
  description = "Fully qualified domain name"
}

output "ecs_service_name" {
  value       = module.nano_idp.ecs_service_name
  description = "ECS service name"
}

output "security_group_id" {
  value       = module.nano_idp.security_group_id
  description = "Security group ID of the NanoIDP task"
}
