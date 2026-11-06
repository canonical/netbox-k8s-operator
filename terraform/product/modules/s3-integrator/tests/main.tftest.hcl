# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

mock_provider "juju" {}

variables {
  model_uuid = "11111111-2222-4333-8444-555555555555"
}

run "basic_plan" {
  command = plan

  assert {
    condition     = output.application.name == "s3-integrator"
    error_message = "s3-integrator application name did not match expected"
  }

  assert {
    condition     = output.provides.s3_credentials.endpoint == "s3-credentials"
    error_message = "s3-integrator provides.s3_credentials endpoint did not match expected"
  }
}
