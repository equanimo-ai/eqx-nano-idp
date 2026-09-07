output "ecr_repository_url" {
  value       = aws_ecr_repository.this.repository_url
  description = "ECR repository URL for NanoIDP container images"
}

output "config_bucket_name" {
  value       = aws_s3_bucket.config.id
  description = "S3 bucket managing NanoIDP configuration"
}

output "config_bucket_arn" {
  value       = aws_s3_bucket.config.arn
  description = "ARN of S3 configuration bucket"
}

output "issuer_url" {
  value       = local.issuer_url
  description = "Public OIDC Issuer URL for NanoIDP"
}

output "fqdn" {
  value       = local.fqdn
  description = "Fully qualified domain name"
}

output "ecs_service_name" {
  value       = aws_ecs_service.this.name
  description = "ECS service name"
}

output "security_group_id" {
  value       = aws_security_group.this.id
  description = "Security group ID of the NanoIDP task"
}
