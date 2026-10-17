# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

run "setup_tests" {
  module {
    source = "./tests/setup"
  }
}

run "basic_deploy_charm" {
  variables {
    model_uuid = run.setup_tests.model_uuid
    channel    = "latest/edge"
    # renovate: depName="netbox-k8s"
    revision = 3
  }

  assert {
    condition     = output.application.name == "netbox-k8s"
    error_message = "netbox-k8s application name did not match expected"
  }
}
