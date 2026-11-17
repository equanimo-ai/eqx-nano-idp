# eqx-nano-idp decommission. The module is removed, so its resources are destroyed on the
# next apply EXCEPT the ones below, which are left in AWS and dropped from Terraform state:
#   - config bucket + seed objects (seeded user data; kept until a data decision is made)
#   - ECR repository (images kept)
#   - Route53 record idp.<env> (DNS unchanged)
# Requires Terraform >= 1.7 (removed blocks), see versions.tf.

removed {
  from = module.nano_idp.aws_s3_bucket.config
  lifecycle {
    destroy = false
  }
}

removed {
  from = module.nano_idp.aws_s3_bucket_versioning.config
  lifecycle {
    destroy = false
  }
}

removed {
  from = module.nano_idp.aws_s3_bucket_public_access_block.config
  lifecycle {
    destroy = false
  }
}

removed {
  from = module.nano_idp.aws_s3_bucket_server_side_encryption_configuration.config
  lifecycle {
    destroy = false
  }
}

removed {
  from = module.nano_idp.aws_s3_bucket_policy.config
  lifecycle {
    destroy = false
  }
}

removed {
  from = module.nano_idp.aws_s3_object.seed_settings
  lifecycle {
    destroy = false
  }
}

removed {
  from = module.nano_idp.aws_s3_object.seed_users
  lifecycle {
    destroy = false
  }
}

removed {
  from = module.nano_idp.aws_ecr_repository.this
  lifecycle {
    destroy = false
  }
}

removed {
  from = module.nano_idp.aws_route53_record.this
  lifecycle {
    destroy = false
  }
}
