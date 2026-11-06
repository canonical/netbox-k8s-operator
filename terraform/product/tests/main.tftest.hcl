# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

mock_provider "juju" {}

variables {
  model_uuid                    = "11111111-2222-4333-8444-555555555555"
  netbox_k8s                    = {}
  oauth_external_idp_integrator = {}
  redis_k8s                     = {}
  s3                            = {}
}

run "basic_plan" {
  command = plan

  assert {
    condition     = output.models.netbox.components.netbox_k8s.name == "netbox-k8s"
    error_message = "netbox-k8s component name did not match expected"
  }

  assert {
    condition     = output.models.netbox.components.redis_k8s.name == "redis-k8s"
    error_message = "redis-k8s component name did not match expected"
  }

  assert {
    condition     = output.models.netbox.components.s3.name == "s3-integrator"
    error_message = "s3-integrator component name did not match expected"
  }

  assert {
    condition     = output.models.netbox.components.oauth_external_idp_integrator.name == "oauth-external-idp-integrator"
    error_message = "oauth-external-idp-integrator component name did not match expected"
  }

  assert {
    condition     = output.metadata.version != ""
    error_message = "metadata.version must not be empty"
  }
}
