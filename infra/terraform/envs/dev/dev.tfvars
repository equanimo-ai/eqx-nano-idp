environment   = "dev"
aws_region    = "us-east-1"
image_tag     = "latest"
cpu           = 256
memory        = 512
desired_count = 1
domain_prefix = "idp"

# Dev runs on Spot: ~70% cheaper, and a reclaimed task is rescheduled by ECS.
capacity_provider_strategy = [{ capacity_provider = "FARGATE_SPOT", weight = 100 }]

# Off-hours window: stop 22:00, start 07:30 daily, America/Chicago (Central).
schedule_stop_cron  = "cron(0 22 * * ? *)"
schedule_start_cron = "cron(30 7 * * ? *)"
schedule_timezone   = "America/Chicago"
