# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "application" {
  description = "The deployed application object."
  value       = juju_application.oauth_external_idp_integrator
}

output "provides" {
  description = "Map of the provided integration endpoints."
  value = {
    oauth = {
      kind       = "endpoint"
      name       = juju_application.oauth_external_idp_integrator.name
      endpoint   = "oauth"
      controller = null
    }
  }
}

output "requires" {
  description = "Map of the required integration endpoints."
  value       = {}
}
