data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

data "aws_ssm_parameter" "vpc_id" {
  name = "/apc/${var.environment}/deploy/vpc/id"
}

data "aws_ssm_parameter" "vpc_private_subnet_ids" {
  name = "/apc/${var.environment}/deploy/vpc/private_subnet_ids"
}

data "aws_ssm_parameter" "ecs_cluster_arn" {
  name = "/apc/${var.environment}/deploy/ecs/cluster_arn"
}

data "aws_ssm_parameter" "alb_https_listener_arn" {
  name = "/apc/${var.environment}/deploy/alb/https_listener_arn"
}

data "aws_ssm_parameter" "alb_security_group_id" {
  name = "/apc/${var.environment}/deploy/alb/security_group_id"
}

data "aws_ssm_parameter" "alb_dns_name" {
  name = "/apc/${var.environment}/deploy/alb/dns_name"
}

data "aws_ssm_parameter" "hosted_zone_id" {
  name = "/apc/${var.environment}/deploy/dns/hosted_zone_id"
}

data "aws_ssm_parameter" "service_discovery_namespace" {
  name = "/apc/${var.environment}/deploy/ecs/service_discovery_namespace"
}

data "aws_route53_zone" "primary" {
  zone_id = data.aws_ssm_parameter.hosted_zone_id.value
}

locals {
  private_subnet_ids = split(",", data.aws_ssm_parameter.vpc_private_subnet_ids.value)

  # S3 Configuration bucket name carries environment per §I.13.2
  config_bucket_name = "eqx-nano-idp-config-${var.environment}"

  # Fully qualified domain name for NanoIDP in dev (e.g. idp.dev.equanimo.io)
  fqdn = "${var.domain_prefix}.${trimsuffix(data.aws_route53_zone.primary.name, ".")}"

  # Issuer URL for OIDC discovery
  issuer_url = "https://${local.fqdn}"

  container_port = 8000
}
