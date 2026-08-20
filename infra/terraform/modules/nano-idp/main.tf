# ── S3 Configuration Bucket ──────────────────────────────────────────────────
resource "aws_s3_bucket" "config" {
  bucket        = local.config_bucket_name
  force_destroy = true
  tags          = merge(var.common_tags, { Name = local.config_bucket_name })
}

resource "aws_s3_bucket_versioning" "config" {
  bucket = aws_s3_bucket.config.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "config" {
  bucket                  = aws_s3_bucket.config.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "config" {
  bucket = aws_s3_bucket.config.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

data "aws_iam_policy_document" "config_bucket_policy" {
  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.config.arn, "${aws_s3_bucket.config.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "config" {
  bucket     = aws_s3_bucket.config.id
  policy     = data.aws_iam_policy_document.config_bucket_policy.json
  depends_on = [aws_s3_bucket_public_access_block.config]
}

# Seed default settings.yaml into S3 config bucket
resource "aws_s3_object" "seed_settings" {
  bucket                 = aws_s3_bucket.config.id
  key                    = "settings.yaml"
  source                 = "${path.module}/../../../../config/settings.yaml"
  etag                   = filemd5("${path.module}/../../../../config/settings.yaml")
  server_side_encryption = "AES256"

  lifecycle {
    ignore_changes = [etag, version_id]
  }
}

# Seed default users.yaml into S3 config bucket
resource "aws_s3_object" "seed_users" {
  bucket                 = aws_s3_bucket.config.id
  key                    = "users.yaml"
  source                 = "${path.module}/../../../../config/users.yaml"
  etag                   = filemd5("${path.module}/../../../../config/users.yaml")
  server_side_encryption = "AES256"

  lifecycle {
    ignore_changes = [etag, version_id]
  }
}

# ── ECR Repository ───────────────────────────────────────────────────────────
resource "aws_ecr_repository" "this" {
  name                 = var.name_prefix
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
  tags = var.common_tags
}

resource "aws_ecr_lifecycle_policy" "this" {
  repository = aws_ecr_repository.this.name
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

# ── IAM Roles ─────────────────────────────────────────────────────────────────
resource "aws_iam_role" "execution" {
  name = "${var.name_prefix}-exec-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "task" {
  name = "${var.name_prefix}-task-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
  tags = var.common_tags
}

# Scoped S3 access policy for Task Role to read/write configuration
resource "aws_iam_role_policy" "task_s3_config" {
  name = "s3-config-access"
  role = aws_iam_role.task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.config.arn,
          "${aws_s3_bucket.config.arn}/*"
        ]
      }
    ]
  })
}

# ── CloudWatch Logs ──────────────────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/ecs/${var.name_prefix}"
  retention_in_days = 14
  tags              = var.common_tags
}

# ── Security Group ───────────────────────────────────────────────────────────
resource "aws_security_group" "this" {
  name        = "${var.name_prefix}-sg"
  description = "Security group for NanoIDP ECS task"
  vpc_id      = data.aws_ssm_parameter.vpc_id.value
  tags        = merge(var.common_tags, { Name = "${var.name_prefix}-sg" })

  ingress {
    description     = "Port 8000 from ALB"
    from_port       = local.container_port
    to_port         = local.container_port
    protocol        = "tcp"
    security_groups = [data.aws_ssm_parameter.alb_security_group_id.value]
  }

  egress {
    description = "Outbound to all (VPC & Internet for S3/ECR)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ── Target Group & ALB Routing ────────────────────────────────────────────────
resource "aws_lb_target_group" "this" {
  name                 = "${var.name_prefix}-tg"
  port                 = local.container_port
  protocol             = "HTTP"
  vpc_id               = data.aws_ssm_parameter.vpc_id.value
  target_type          = "ip"
  deregistration_delay = 30

  health_check {
    enabled             = true
    path                = "/api/health"
    protocol            = "HTTP"
    port                = "traffic-port"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
    matcher             = "200"
  }

  tags = var.common_tags
}

resource "aws_lb_listener_rule" "this" {
  listener_arn = data.aws_ssm_parameter.alb_https_listener_arn.value
  priority     = 110

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.this.arn
  }

  condition {
    host_header {
      values = [local.fqdn]
    }
  }

  tags = var.common_tags
}

# Route53 DNS record pointing to shared ALB
resource "aws_route53_record" "this" {
  zone_id = data.aws_ssm_parameter.hosted_zone_id.value
  name    = local.fqdn
  type    = "CNAME"
  ttl     = 300
  records = [data.aws_ssm_parameter.alb_dns_name.value]
}

# ── Service Discovery ─────────────────────────────────────────────────────────
resource "aws_service_discovery_service" "this" {
  name = "nano-idp"

  dns_config {
    namespace_id = data.aws_ssm_parameter.service_discovery_namespace.value
    dns_records {
      ttl  = 10
      type = "A"
    }
    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = var.common_tags
}

# ── ECS Task Definition & Service ────────────────────────────────────────────
resource "aws_ecs_task_definition" "this" {
  family                   = var.name_prefix
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  container_definitions = jsonencode([
    {
      name      = var.name_prefix
      image     = "${aws_ecr_repository.this.repository_url}:${var.image_tag}"
      essential = true

      portMappings = [
        {
          containerPort = local.container_port
          hostPort      = local.container_port
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "PORT", value = tostring(local.container_port) },
        { name = "NANOIDP_CONFIG_DIR", value = "/app/config" },
        { name = "NANOIDP_S3_CONFIG_BUCKET", value = aws_s3_bucket.config.id },
        { name = "NANOIDP_S3_CONFIG_PREFIX", value = "" },
        { name = "OAUTH_ISSUER", value = local.issuer_url },
        { name = "CLERK_ENABLED", value = "true" }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.this.name
          "awslogs-region"        = data.aws_region.current.id
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -fsSL http://localhost:${local.container_port}/api/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 15
      }
    }
  ])

  tags = var.common_tags
}

resource "aws_ecs_service" "this" {
  name            = var.name_prefix
  cluster         = data.aws_ssm_parameter.ecs_cluster_arn.value
  task_definition = aws_ecs_task_definition.this.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = local.private_subnet_ids
    security_groups  = [aws_security_group.this.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.this.arn
    container_name   = var.name_prefix
    container_port   = local.container_port
  }

  service_registries {
    registry_arn = aws_service_discovery_service.this.arn
  }

  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  tags = var.common_tags
}

# ── SSM Deploy Contract Publication ──────────────────────────────────────────
resource "aws_ssm_parameter" "issuer_url" {
  name      = "/apc/${var.environment}/deploy/nano_idp/issuer_url"
  type      = "String"
  value     = local.issuer_url
  overwrite = true
  tags      = var.common_tags
}

resource "aws_ssm_parameter" "config_bucket" {
  name      = "/apc/${var.environment}/deploy/nano_idp/config_bucket"
  type      = "String"
  value     = aws_s3_bucket.config.id
  overwrite = true
  tags      = var.common_tags
}

resource "aws_ssm_parameter" "ecr_repo_url" {
  name      = "/apc/${var.environment}/deploy/nano_idp/ecr_repo_url"
  type      = "String"
  value     = aws_ecr_repository.this.repository_url
  overwrite = true
  tags      = var.common_tags
}
