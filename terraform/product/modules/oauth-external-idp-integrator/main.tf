# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

resource "juju_application" "oauth_external_idp_integrator" {
  name  = var.app_name
  model = var.model

  charm {
    name     = "oauth-external-idp-integrator"
    channel  = var.channel
    revision = var.revision
    base     = var.base
  }

  config      = var.config
  constraints = var.constraints
  units       = var.units
}
