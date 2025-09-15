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

module "postgresql_k8s" {
  source          = "git::https://github.com/canonical/postgresql-k8s-operator//terraform"
  app_name        = var.postgresql_k8s.app_name
  channel         = var.postgresql_k8s.channel
  config          = var.postgresql_k8s.config
  constraints     = var.postgresql_k8s.constraints
  juju_model_name = data.juju_model.netbox_k8s.name
  revision        = var.postgresql_k8s.revision
  base            = var.postgresql_k8s.base
  units           = var.postgresql_k8s.units

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

module self_signed_certificates {
  source      = "./modules/self-signed-certificates"
  app_name    = var.self_signed_certificates.app_name
  channel     = var.self_signed_certificates.channel
  config      = var.self_signed_certificates.config
  constraints = var.self_signed_certificates.constraints
  model       = data.juju_model.netbox_k8s.name
  revision    = var.self_signed_certificates.revision
  base        = var.self_signed_certificates.base
  units       = var.self_signed_certificates.units
}

resource "juju_integration" "netbox_postgresql_database" {
  model = data.juju_model.netbox_k8s.name

  application {
    name     = module.netbox_k8s.app_name
    endpoint = module.netbox_k8s.requires.postgresql
  }

  application {
    name     = module.postgresql_k8s.application_name
    endpoint = module.postgresql_k8s.provides.database
  }
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
    name     = module.self_signed_certificates.app_name
    endpoint = module.self_signed_certificates.provides.certificates
  }
}
