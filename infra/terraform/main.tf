data "aws_ssm_parameter" "hosted_zone_id" {
  name = "/apc/${var.environment}/deploy/dns/hosted_zone_id"
}

data "aws_ssm_parameter" "alb_dns_name" {
  name = "/apc/${var.environment}/deploy/alb/dns_name"
}

import {
  to = aws_s3_bucket.config
  id = "eqx-nano-idp-config-dev"
}

import {
  to = aws_ecr_repository.kept
  id = "eqx-nano-idp"
}

import {
  to = aws_route53_record.idp
  id = "${data.aws_ssm_parameter.hosted_zone_id.value}_idp.dev.equanimo.io_CNAME"
}

resource "aws_s3_bucket" "config" {
  bucket        = "eqx-nano-idp-config-dev"
  force_destroy = true
}

resource "aws_ecr_repository" "kept" {
  name                 = "eqx-nano-idp"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_route53_record" "idp" {
  zone_id = data.aws_ssm_parameter.hosted_zone_id.value
  name    = "idp.dev.equanimo.io"
  type    = "CNAME"
  ttl     = 300
  records = [data.aws_ssm_parameter.alb_dns_name.value]
}

resource "aws_ecr_lifecycle_policy" "nano_idp" {
  repository = aws_ecr_repository.kept.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 30 tagged images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 30
      }
      action = { type = "expire" }
    }]
  })
}
