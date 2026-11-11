# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "model_uuid" {
  description = "Reference to the k8s Juju model's uuid to deploy application to."
  type        = string
}

variable "netbox_k8s" {
  type = object({
    app_name    = optional(string, "netbox-k8s")
    channel     = optional(string, "4/edge")
    config      = optional(map(string), {})
    constraints = optional(string, "arch=amd64")
    revision    = optional(number)
    base        = optional(string, "ubuntu@26.04")
    units       = optional(number, 1)
  })
}

variable "valkey" {
  type = object({
    app_name = optional(string, "valkey")
    channel  = optional(string, "9/edge")
    config   = optional(map(string), {})
    revision = optional(number, null)
    base     = optional(string, "ubuntu@26.04")
    units    = optional(number, 1)
  })
  default = {}
}

variable "redis_k8s" {
  description = "Removed. NetBox now uses Valkey, set the valkey variable instead."
  type        = any
  default     = null

  validation {
    condition     = var.redis_k8s == null
    error_message = "The redis_k8s variable was removed because the product module deploys Valkey instead of Redis. Remove it and use the valkey variable instead. See docs/how-to/migrate-to-26.04-and-valkey.md."
  }
}

variable "s3" {
  type = object({
    app_name    = optional(string, "s3-integrator")
    channel     = optional(string, "latest/stable")
    config      = optional(map(string), {})
    constraints = optional(string, "arch=amd64")
    revision    = optional(number, null)
    base        = optional(string, "ubuntu@22.04")
    units       = optional(number, 1)
    storage     = optional(map(string), {})
  })
}

variable "oauth_external_idp_integrator" {
  type = object({
    app_name    = optional(string, "oauth-external-idp-integrator")
    channel     = optional(string, "latest/edge")
    config      = optional(map(string), {})
    constraints = optional(string, "arch=amd64")
    revision    = optional(number, 6)
    base        = optional(string, "ubuntu@22.04")
    units       = optional(number, 1)
  })
}
