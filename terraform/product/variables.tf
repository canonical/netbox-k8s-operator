# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "model" {
  description = "Reference to the k8s Juju model to deploy application to."
  type        = string
}

variable "model_user" {
  description = "Juju user used for deploying the application."
  type        = string
}

variable "netbox_k8s" {
  type = object({
    app_name    = optional(string, "netbox-k8s")
    channel     = optional(string, "latest/edge")
    config      = optional(map(string), { }) 
    constraints = optional(string, "arch=amd64")
    revision    = optional(number)
    base        = optional(string, "ubuntu@22.04")
    units       = optional(number, 1)
  })

}

variable "postgresql_k8s" {
  type = object({
    app_name    = optional(string, "postgresql-k8s")
    channel     = optional(string, "14/stable")
    config      = optional(map(string), {})
    constraints = optional(string, "arch=amd64")
    revision    = optional(number, 495)
    base        = optional(string, "ubuntu@22.04")
    units       = optional(number, 1)
  })
}

variable "saml_integrator" {
  type = object({
    app_name    = optional(string, "saml-integrator")
    channel     = optional(string, "latest/stable")
    config      = optional(map(string), {})
    constraints = optional(string, "arch=amd64")
    revision    = optional(number)
    base        = optional(string, "ubuntu@22.04")
    units       = optional(number, 1)
  })
}

variable "traefik_k8s" {
  type = object({
    app_name    = optional(string, "traefik-k8s")
    channel     = optional(string, "latest/stable")
    config      = optional(map(string), {})
    constraints = optional(string, "arch=amd64")
    revision    = optional(number)
    base        = optional(string, "ubuntu@20.04")
    units       = optional(number, 1)
    storage     = optional(map(string), {})
  })
}

variable "redis_k8s" {
  type = object({
    app_name    = optional(string, "redis-k8s")
    channel     = optional(string, "latest/edge")
    config      = optional(map(string), {})
    constraints = optional(string, "arch=amd64")
    revision    = optional(number, null)
    base        = optional(string, "ubuntu@22.04")
    units       = optional(number, 1)
    storage     = optional(map(string), {})
  })
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