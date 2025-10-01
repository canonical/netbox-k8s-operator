# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  description = "Name of the deployed application."
  value       = juju_application.self_signed_certificates.name
}

output "requires" {
  value = {
    logging = "logging"
  }
}

output "provides" {
  value = {
    certificates = "certificates"
    send-ca-cert = "send-ca-cert"
  }
}
