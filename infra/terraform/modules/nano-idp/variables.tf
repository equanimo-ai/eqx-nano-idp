variable "environment" {
  type = string
}

variable "name_prefix" {
  type    = string
  default = "eqx-nano-idp"
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "cpu" {
  type    = number
  default = 256
}

variable "memory" {
  type    = number
  default = 512
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "is_production_account" {
  type    = bool
  default = false
}

variable "domain_prefix" {
  type    = string
  default = "idp"
}

variable "common_tags" {
  type    = map(string)
  default = {}
}
