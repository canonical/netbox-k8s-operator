# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "ingress_requires" {
  value = {
    certificates = "certificates"
    logging      = "logging"
  }
}

output "ingress_provides" {
  value = {
    grafana_dashboard = "grafana-dashboard"
    metrics_endpoint  = "metrics-endpoint"
  }
}

output "netbox_app_name" {
  description = "Name of the deployed application."
  value       = module.netbox_k8s.app_name
}

output "netbox_requires" {
  value = {
    logging = "logging"
  }
}

output "netbox_provides" {
  value = {
    grafana_dashboard = "grafana-dashboard"
    metrics_endpoint  = "metrics-endpoint"
  }
}
