# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

data "juju_model" "netbox" {
  name = var.model
}

module "netbox_k8s" {
  source      = "../charm"
  app_name    = var.netbox.app_name
  channel     = var.netbox.channel
  config      = var.netbox.config
  model       = data.juju_model.netbox.name
  constraints = var.netbox.constraints
  revision    = var.netbox.revision
  base        = var.netbox.base
  units       = var.netbox.units
}

module "postgresql" {
  source          = "git::https://github.com/canonical/postgresql-operator//terraform"
  app_name        = var.postgresql.app_name
  channel         = var.postgresql.channel
  config          = var.postgresql.config
  constraints     = var.postgresql.constraints
  juju_model_name = data.juju_model.netbox.name
  revision        = var.postgresql.revision
  base            = var.postgresql.base
  units           = var.postgresql.units

}

module "saml_integrator" {
  source          = "git::https://github.com/canonical/saml-integrator-operator//terraform"
  app_name        = var.saml_integrator.app_name
  channel         = var.saml_integrator.channel
  config          = var.saml_integrator.config
  constraints     = var.saml_integrator.constraints
  juju_model_name = data.juju_model.netbox.name
  revision        = var.saml_integrator.revision
  base            = var.saml_integrator.base
  units           = var.saml_integrator.units

}

module "redis_k8s" {
  source      = "./modules/redis-k8s"
  app_name    = var.redis_k8s.app_name
  channel     = var.redis_k8s.channel
  config      = var.redis_k8s.config
  constraints = var.redis_k8s.constraints
  model       = data.juju_model.netbox.name
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
  model       = data.juju_model.netbox.name
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
  model       = data.juju_model.netbox.name
  revision    = var.traefik_k8s.revision
  base        = var.traefik_k8s.base
  units       = var.traefik_k8s.units
}

resource "juju_integration" "netbox_postgresql_database" {
  model = data.juju_model.netbox.name

  application {
    name     = module.netbox_k8s.app_name
    endpoint = module.netbox_k8s.requires.postgresql
  }

  application {
    name     = module.postgresql.app_name
    endpoint = module.postgresql.provides.ingress
  }
}

resource "juju_integration" "netbox_redis" {
  model = data.juju_model.netbox.name

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
  model = data.juju_model.netbox.name

  application {
    name     = module.netbox_k8s.app_name
    endpoint = module.netbox_k8s.requires.s3
  }

  application {
    name     = module.s3.app_name
    endpoint = module.s3.provides.s3
  }
}

# resource "juju_integration" "netbox_traefik_nginx" {
#   model = data.juju_model.netbox.name

#   application {
#     name     = module.netbox_k8s.app_name
#     endpoint = module.netbox_k8s.requires.ingress
#   }

#   application {
#     name     = module.traefik_k8s.app_name
#     endpoint = module.traefik_k8s.provides.ingress
#   }
# }

# resource "juju_integration" "netbox_traefik_traefik_route" {
#   model = data.juju_model.netbox.name

#   application {
#     name     = module.netbox_k8s.app_name
#     endpoint = module.netbox_k8s.requires.traefik_route
#   }

#   application {
#     name     = module.traefik_k8s.app_name
#     endpoint = module.traefik_k8s.provides.traefik_route
#   }
# }
