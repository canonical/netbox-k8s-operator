<!-- vale Canonical.007-Headings-sentence-case = NO -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

* Breaking: update NetBox to 4.7.5, which requires PostgreSQL 15 or later. PostgreSQL 14 is no
  longer supported. If the PostgreSQL integration publishes its version and it is lower than 15,
  the charm is blocked and does not start NetBox. Migrate your data to PostgreSQL 15 or later
  before upgrading. See [Upgrade to NetBox 4.7](how-to/upgrade-to-netbox-4.7.md).
* Publish NetBox 4.7 to the new `4.7` track. The `4` track stays on NetBox 4.6. The Terraform
  modules default to `4.7/edge`.
* Remove the daily `housekeeping` command from the scheduler. NetBox 4.7 removed it and runs
  housekeeping as a system job in the RQ worker.
* Move the charm and rock to Ubuntu 26.04 LTS and migrate to paas-charm v2.
* Add a Valkey integration (`valkey` endpoint, `valkey_client`
  interface) alongside the `redis` integration. The charm is blocked unless
  exactly one of them is integrated.
* Breaking: the `terraform/product` module deploys Valkey instead of Redis. The
  `redis_k8s` variable is replaced by `valkey`, and setting `redis_k8s` fails
  validation. The module requires the
  Juju Terraform provider 2.2.1 or later.
* Rename the OCI resource `django-app-image` to `app-image`.
* Replace Ubuntu `cron` with Supercronic, running unprivileged.
* Stop rock builds when source preparation fails and restore the additional
  dependencies required by NetBox, including WhiteNoise.
* Add OIDC group synchronization with configurable staff and superuser groups.
* Add `CSRF_TRUSTED_ORIGINS` setting to the configuration file to prevent
  login failures when NetBox is behind a reverse proxy.

## 2025-12-17

- Moved charm-architecture.md from Explanation to Reference category.

## 2025-11-11

- Add missing outputs to the Terraform product module.

## 2025-09-25

* Update documentation.

## 2025-09-12

* Add OIDC integration.

## 2025-09-3

* Initialized the repository.
