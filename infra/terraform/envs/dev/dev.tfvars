environment   = "dev"
aws_region    = "us-east-1"
image_tag     = "latest"
cpu           = 256
memory        = 512
desired_count = 1
domain_prefix = "idp"

# Dev runs on Spot: ~70% cheaper, and a reclaimed task is rescheduled by ECS.
capacity_provider_strategy = [{ capacity_provider = "FARGATE_SPOT", weight = 100 }]
