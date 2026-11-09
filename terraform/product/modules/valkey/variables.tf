# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "app_name" {
  description = "Name of the application in the Juju model."
  type        = string
  default     = "valkey"
}

variable "channel" {
  description = "The channel to use when deploying a charm."
  type        = string
  default     = "9/edge"
}

variable "config" {
  description = "Application config. Details about available options can be found at https://charmhub.io/valkey/configure."
  type        = map(string)
  default     = {}
}

variable "model_uuid" {
  description = "Reference to a juju model's uuid."
  type        = string
}

variable "revision" {
  description = "Revision number of the charm"
  type        = number
  default     = null
}

variable "base" {
  description = "The operating system on which to deploy"
  type        = string
  default     = "ubuntu@26.04"
}

variable "units" {
  description = "Number of units to deploy"
  type        = number
  default     = 1
}
