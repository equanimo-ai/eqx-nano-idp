# Business-hours scale-to-zero schedule matching other ECS microservices
# (eqx-embedding-service, eqx-policy-dsl-compiler, eqx-evaluation-api).
# Window: 09:00 - 00:00 America/New_York (09:00 AM - Midnight ET).
#
# EventBridge Scheduler's ECS "universal target" calls ecs:UpdateService
# directly -- no Lambda needed.
# The other half of the mechanism is aws_ecs_service.this lifecycle
# `ignore_changes = [task_definition, desired_count]`.

resource "aws_iam_role" "scheduler" {
  count = var.enable_off_hours_schedule ? 1 : 0

  name = "${var.name_prefix}-scheduler"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy" "scheduler" {
  count = var.enable_off_hours_schedule ? 1 : 0

  name = "${var.name_prefix}-scheduler"
  role = aws_iam_role.scheduler[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ScaleNanoIdpService"
      Effect   = "Allow"
      Action   = ["ecs:UpdateService"]
      Resource = [aws_ecs_service.this.id]
    }]
  })
}

resource "aws_scheduler_schedule" "start" {
  count = var.enable_off_hours_schedule ? 1 : 0

  name                         = "${var.name_prefix}-start"
  schedule_expression          = var.schedule_start_cron
  schedule_expression_timezone = var.schedule_timezone

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = "arn:aws:scheduler:::aws-sdk:ecs:updateService"
    role_arn = aws_iam_role.scheduler[0].arn
    input = jsonencode({
      Cluster      = data.aws_ssm_parameter.ecs_cluster_arn.value
      Service      = aws_ecs_service.this.name
      DesiredCount = var.desired_count
    })
  }
}

resource "aws_scheduler_schedule" "stop" {
  count = var.enable_off_hours_schedule ? 1 : 0

  name                         = "${var.name_prefix}-stop"
  schedule_expression          = var.schedule_stop_cron
  schedule_expression_timezone = var.schedule_timezone

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = "arn:aws:scheduler:::aws-sdk:ecs:updateService"
    role_arn = aws_iam_role.scheduler[0].arn
    input = jsonencode({
      Cluster      = data.aws_ssm_parameter.ecs_cluster_arn.value
      Service      = aws_ecs_service.this.name
      DesiredCount = 0
    })
  }
}
