# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

data "juju_model" "netbox_k8s" {
  name  = var.model
}

module "netbox_k8s" {
  source      = "../charm"
  app_name    = var.netbox_k8s.app_name
  channel     = var.netbox_k8s.channel
  config      = var.netbox_k8s.config
  model_uuid  = data.juju_model.netbox_k8s.uuid
  constraints = var.netbox_k8s.constraints
  revision    = var.netbox_k8s.revision
  base        = var.netbox_k8s.base
  units       = var.netbox_k8s.units
}

module "redis_k8s" {
  source      = "./modules/redis-k8s"
  app_name    = var.redis_k8s.app_name
  channel     = var.redis_k8s.channel
  config      = var.redis_k8s.config
  constraints = var.redis_k8s.constraints
  model_uuid  = data.juju_model.netbox_k8s.uuid
  revision    = var.redis_k8s.revision
  base        = var.redis_k8s.base
  units       = var.redis_k8s.units
}

module "s3" {
  source      = "./modules/s3-integrator"
  app_name    = var.s3.app_name
  channel     = var.s3.channel
  config      = var.s3.config
  constraints = var.s3.constraints
  model_uuid  = data.juju_model.netbox_k8s.uuid
  revision    = var.s3.revision
  base        = var.s3.base
  units       = var.s3.units
}

module "gateway_api_integrator" {
  source      = "./modules/gateway-api-integrator"
  app_name    = var.gateway_api_integrator.app_name
  channel     = var.gateway_api_integrator.channel
  config      = var.gateway_api_integrator.config
  constraints = var.gateway_api_integrator.constraints
  model_uuid  = data.juju_model.netbox_k8s.uuid
  revision    = var.gateway_api_integrator.revision
  base        = var.gateway_api_integrator.base
  units       = var.gateway_api_integrator.units
}

module "gateway_route_configurator" {
  source      = "./modules/gateway-route-configurator"
  app_name    = var.gateway_route_configurator.app_name
  channel     = var.gateway_route_configurator.channel
  config      = var.gateway_route_configurator.config
  constraints = var.gateway_route_configurator.constraints
  model_uuid  = data.juju_model.netbox_k8s.uuid
  revision    = var.gateway_route_configurator.revision
  base        = var.gateway_route_configurator.base
  units       = var.gateway_route_configurator.units
}

module "oauth_external_idp_integrator" {
  source      = "./modules/oauth-external-idp-integrator"
  app_name    = var.oauth_external_idp_integrator.app_name
  channel     = var.oauth_external_idp_integrator.channel
  config      = var.oauth_external_idp_integrator.config
  constraints = var.oauth_external_idp_integrator.constraints
  model_uuid  = data.juju_model.netbox_k8s.uuid
  revision    = var.oauth_external_idp_integrator.revision
  base        = var.oauth_external_idp_integrator.base
  units       = var.oauth_external_idp_integrator.units
}

resource "juju_integration" "netbox_redis" {
  model_uuid = data.juju_model.netbox_k8s.uuid

  application {
    name     = module.netbox_k8s.app_name
    endpoint = module.netbox_k8s.requires.redis
  }

  application {
    name     = module.redis_k8s.app_name
    endpoint = module.redis_k8s.provides.redis
  }
}

resource "juju_integration" "netbox_s3" {
  model_uuid = data.juju_model.netbox_k8s.uuid

  application {
    name     = module.netbox_k8s.app_name
    endpoint = module.netbox_k8s.requires.s3
  }

  application {
    name     = module.s3.app_name
    endpoint = module.s3.provides.s3_credentials
  }
}

resource "juju_integration" "netbox_ingress" {
  model_uuid = data.juju_model.netbox_k8s.uuid

  application {
    name     = module.netbox_k8s.app_name
    endpoint = module.netbox_k8s.requires.ingress
  }

  application {
    name     = module.gateway_route_configurator.app_name
    endpoint = module.gateway_route_configurator.provides.ingress
  }
}

resource "juju_integration" "gateway_route" {
  model_uuid = data.juju_model.netbox_k8s.uuid

  application {
    name     = module.gateway_route_configurator.app_name
    endpoint = module.gateway_route_configurator.requires.gateway_route
  }

  application {
    name     = module.gateway_api_integrator.app_name
    endpoint = module.gateway_api_integrator.provides.gateway_route
  }
}

resource "juju_integration" "netbox_oidc" {
  model_uuid = data.juju_model.netbox_k8s.uuid

  application {
    name     = module.netbox_k8s.app_name
    endpoint = module.netbox_k8s.requires.oidc
  }

  application {
    name     = module.oauth_external_idp_integrator.app_name
    endpoint = module.oauth_external_idp_integrator.provides.oauth
  }
}
