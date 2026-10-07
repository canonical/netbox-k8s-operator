# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "application" {
  description = "The deployed application object."
  value       = juju_application.redis_k8s
}

output "provides" {
  description = "Map of the provided integration endpoints."
  value = {
    redis = {
      kind       = "endpoint"
      name       = juju_application.redis_k8s.name
      endpoint   = "redis"
      controller = null
    }
  }
}

output "requires" {
  description = "Map of the required integration endpoints."
  value       = {}
}
