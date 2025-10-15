# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  description = "Name of the deployed application."
  value       = juju_application.oauth_external_idp_integrator.name
}

output "requires" {
  value = {
  }
}

output "provides" {
  value = {
    oauth = "oauth"
  }
}
