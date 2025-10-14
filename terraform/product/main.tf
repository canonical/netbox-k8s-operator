# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

data "juju_model" "netbox_k8s" {
  name = var.model
}

module "netbox_k8s" {
  source      = "../charm"
  app_name    = var.netbox_k8s.app_name
  channel     = var.netbox_k8s.channel
  config      = var.netbox_k8s.config
  model       = data.juju_model.netbox_k8s.name
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
  model       = data.juju_model.netbox_k8s.name
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
  model       = data.juju_model.netbox_k8s.name
  revision    = var.s3.revision
  base        = var.s3.base
  units       = var.s3.units
}

module "traefik_k8s" {
  source      = "./modules/traefik-k8s"
  app_name    = var.traefik_k8s.app_name
  channel     = var.traefik_k8s.channel
  config      = var.traefik_k8s.config
  constraints = var.traefik_k8s.constraints
  model       = data.juju_model.netbox_k8s.name
  revision    = var.traefik_k8s.revision
  base        = var.traefik_k8s.base
  units       = var.traefik_k8s.units
}

module "httprequest_lego_k8s" {
  source      = "./modules/httprequest-lego-k8s"
  app_name    = var.httprequest_lego_k8s.app_name
  channel     = var.httprequest_lego_k8s.channel
  config      = var.httprequest_lego_k8s.config
  constraints = var.httprequest_lego_k8s.constraints
  model       = data.juju_model.netbox_k8s.name
  revision    = var.httprequest_lego_k8s.revision
  base        = var.httprequest_lego_k8s.base
  units       = var.httprequest_lego_k8s.units
}


module "oauth_external_idp_integrator" { 
  source      = "./modules/oauth-external-idp-integrator"
  app_name    = var.oauth_external_idp_integrator.app_name
  channel     = var.oauth_external_idp_integrator.channel
  config      = var.oauth_external_idp_integrator.config
  constraints = var.oauth_external_idp_integrator.constraints
  model       = data.juju_model.netbox_k8s.name
  revision    = var.oauth_external_idp_integrator.revision
  base        = var.oauth_external_idp_integrator.base
  units       = var.oauth_external_idp_integrator.units
}

resource "juju_integration" "netbox_redis" {
  model = data.juju_model.netbox_k8s.name

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
  model = data.juju_model.netbox_k8s.name

  application {
    name     = module.netbox_k8s.app_name
    endpoint = module.netbox_k8s.requires.s3
  }

  application {
    name     = module.s3.app_name
    endpoint = module.s3.provides.s3_credentials
  }
}

resource "juju_integration" "netbox_traefik" {
  model = data.juju_model.netbox_k8s.name

  application {
    name     = module.netbox_k8s.app_name
    endpoint = module.netbox_k8s.requires.ingress
  }

  application {
    name     = module.traefik_k8s.app_name
    endpoint = module.traefik_k8s.provides.ingress
  }
}

resource "juju_integration" "traefik_certs" {
  model = data.juju_model.netbox_k8s.name

  application {
    name     = module.traefik_k8s.app_name
    endpoint = module.traefik_k8s.requires.certificates
  }

  application {
    name     = module.httprequest_lego_k8s.app_name
    endpoint = module.httprequest_lego_k8s.provides.certificates
  }
}

resource "juju_integration" "netbox_oidc" {
  model = data.juju_model.netbox_k8s.name

  application {
    name     = module.netbox_k8s.app_name
    endpoint = module.netbox_k8s.requires.oidc
  }

  application {
    name     = module.oauth_external_idp_integrator.app_name
    endpoint = module.oauth_external_idp_integrator.provides.oauth
  }
}
