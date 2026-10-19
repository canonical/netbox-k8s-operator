# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

mock_provider "juju" {}

variables {
  model_uuid = "11111111-2222-4333-8444-555555555555"
}

run "basic_plan" {
  command = plan

  assert {
    condition     = output.application.name == "oauth-external-idp-integrator"
    error_message = "oauth-external-idp-integrator application name did not match expected"
  }

  assert {
    condition     = output.provides.oauth.endpoint == "oauth"
    error_message = "oauth-external-idp-integrator provides.oauth endpoint did not match expected"
  }
}
