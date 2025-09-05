# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  description = "Name of the deployed application."
  value       = juju_application.netbox_k8s.name
}

output "requires" {
  value = {
    ingress       = "ingress"
    logging       = "logging"
    postgresql    = "postgresql"
    redis         = "redis"
    s3            = "s3"
    saml          = "saml"
  }
}

output "provides" {
  value = {
    grafana_dashboard = "grafana-dashboard"
    metrics_endpoint  = "metrics-endpoint"
  }
}
