# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "metadata" {
  description = "Metadata of the product deployment."
  value = {
    version     = "1.0.0"
    deployed_at = terraform_data.deployed_at.output
    updated_at  = timestamp()
  }
}

output "models" {
  description = "Map of the key of the model and the components deployed in the model."
  value = {
    netbox = {
      model_uuid = data.juju_model.netbox_k8s.uuid
      components = {
        netbox_k8s                    = module.netbox_k8s.application
        oauth_external_idp_integrator = module.oauth_external_idp_integrator.application
        redis_k8s                     = module.redis_k8s.application
        s3                            = module.s3.application
      }
    }
  }
}
