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

  module {
    source = "./charm"
  }

  assert {
    condition     = output.app_name == "netbox-k8s"
    error_message = "netbox-k8s app_name did not match expected"
  }
}
