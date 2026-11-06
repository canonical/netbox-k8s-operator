# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

mock_provider "juju" {}

variables {
  model_uuid = "11111111-2222-4333-8444-555555555555"
}

run "basic_plan" {
  command = plan

  assert {
    condition     = output.application.name == "redis-k8s"
    error_message = "redis-k8s application name did not match expected"
  }

  assert {
    condition     = output.provides.redis.endpoint == "redis"
    error_message = "redis-k8s provides.redis endpoint did not match expected"
  }
}
