# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "app_name" {
  description = "Name of the application in the Juju model."
  type        = string
  default     = "netbox-k8s"
}

variable "channel" {
  description = "The channel to use when deploying a charm."
  type        = string
  default     = "4/edge"
}

variable "config" {
  description = "Application config. Details about available options can be found at https://charmhub.io/netbox-k8s/configurations."
  type        = map(string)
  default     = { "django-debug" : "False", "django-allowed-hosts" : "*" } # Update defaults as appropriate
}

variable "constraints" {
  description = "Juju constraints to apply for this application."
  type        = string
  default     = ""
}

variable "model_uuid" {
  description = "Reference to a juju model's uuid."
  type        = string
  default     = ""
}

variable "revision" {
  description = "Revision number of the charm"
  type        = number
  default     = null
}

variable "base" {
  description = "The operating system on which to deploy"
  type        = string
  default     = "ubuntu@24.04"
}

variable "units" {
  description = "Number of units to deploy"
  type        = number
  default     = 1
}
