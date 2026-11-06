# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "application" {
  description = "The deployed application object."
  value       = juju_application.s3_integrator
}

output "provides" {
  description = "Map of the provided integration endpoints."
  value = {
    s3_credentials = {
      kind       = "endpoint"
      name       = juju_application.s3_integrator.name
      endpoint   = "s3-credentials"
      controller = null
    }
  }
}

output "requires" {
  description = "Map of the required integration endpoints."
  value       = {}
}
