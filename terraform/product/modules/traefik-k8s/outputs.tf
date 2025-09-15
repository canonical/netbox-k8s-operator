# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  description = "Name of the deployed application."
  value       = juju_application.traefik_k8s.name
}

output "requires" {
  value = {
    certificates              = "certificates"
    charm_tracing             = "charm-tracing"
    experimental_forward_auth = "experimental-forward-auth"
    logging                   = "logging"
    receive_ca_cert           = "receive-ca-cert"
    workload_tracing          = "workload-tracing"
  }
}

output "provides" {
  value = {
    ingress           = "ingress"
    grafana_dashboard = "grafana-dashboard"
    ingress_per_unit  = "ingress-per-unit"
    metrics_endpoint  = "metrics-endpoint"
    traefik_route     = "traefik-route"
  }
}
