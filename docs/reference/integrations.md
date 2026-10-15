# Integrations

See [Integrations](https://charmhub.io/netbox-k8s/integrations).

## Cache

Integrate either the existing `redis` endpoint (`redis` interface) or the
`valkey` endpoint (`valkey_client` interface), but not both. Both supply
`REDIS_DB_HOSTNAME`, `REDIS_DB_PORT`, `REDIS_DB_USERNAME`, and
`REDIS_DB_PASSWORD` to NetBox. The tasks and caching databases remain 0 and 1.
Valkey credentials are resolved through the provider's Juju secrets.
TLS-enabled Valkey connections are not supported.

## Custom certificate trust

The optional `certificates` endpoint (`tls-certificates` interface) requests a
certificate for the NetBox application and adds its CA to the workload's system
CA bundle. All workload processes use the combined bundle through
`REQUESTS_CA_BUNDLE` and `SSL_CERT_FILE`. Removing the relation removes the custom
bundle and restores system trust.
