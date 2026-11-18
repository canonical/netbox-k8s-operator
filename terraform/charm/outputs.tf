# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  description = "Name of the deployed application."
  value       = juju_application.netbox_k8s.name
}

output "application" {
  description = "The deployed application object."
  value       = juju_application.netbox_k8s
}

output "requires" {
  description = "Map of the required integration endpoints."
  value = {
    ingress = {
      kind       = "endpoint"
      name       = juju_application.netbox_k8s.name
      endpoint   = "ingress"
      controller = null
    }
    logging = {
      kind       = "endpoint"
      name       = juju_application.netbox_k8s.name
      endpoint   = "logging"
      controller = null
    }
    oidc = {
      kind       = "endpoint"
      name       = juju_application.netbox_k8s.name
      endpoint   = "oidc"
      controller = null
    }
    postgresql = {
      kind       = "endpoint"
      name       = juju_application.netbox_k8s.name
      endpoint   = "postgresql"
      controller = null
    }
    redis = {
      kind       = "endpoint"
      name       = juju_application.netbox_k8s.name
      endpoint   = "redis"
      controller = null
    }
    s3 = {
      kind       = "endpoint"
      name       = juju_application.netbox_k8s.name
      endpoint   = "s3"
      controller = null
    }
    saml = {
      kind       = "endpoint"
      name       = juju_application.netbox_k8s.name
      endpoint   = "saml"
      controller = null
    }
    valkey = {
      kind       = "endpoint"
      name       = juju_application.netbox_k8s.name
      endpoint   = "valkey"
      controller = null
    }
  }
}

output "provides" {
  description = "Map of the provided integration endpoints."
  value = {
    grafana_dashboard = {
      kind       = "endpoint"
      name       = juju_application.netbox_k8s.name
      endpoint   = "grafana-dashboard"
      controller = null
    }
    metrics_endpoint = {
      kind       = "endpoint"
      name       = juju_application.netbox_k8s.name
      endpoint   = "metrics-endpoint"
      controller = null
    }
  }
}
