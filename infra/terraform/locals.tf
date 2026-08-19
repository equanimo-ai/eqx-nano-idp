locals {
  name_prefix = "eqx-nano-idp"

  common_tags = {
    Platform    = "apc"
    Repository  = "eqx-nano-idp"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
