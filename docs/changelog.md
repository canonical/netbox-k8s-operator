<!-- vale Canonical.007-Headings-sentence-case = NO -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

* Pin NetBox to 4.6.10 to retain PostgreSQL 14 compatibility.
* Move the charm and rock to Ubuntu 26.04 and migrate to paas-charm v2.
* Add a Valkey integration (`valkey_netbox` endpoint, `valkey_client`
  interface) alongside the `redis` integration. The charm is blocked if both
  are integrated at the same time.
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
