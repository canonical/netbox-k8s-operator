# Integrations

See [Integrations](https://charmhub.io/netbox-k8s/integrations).

## Cache

NetBox needs exactly one cache integration: `redis` (`redis` interface) or
`valkey_netbox` (`valkey_client` interface). Both supply `REDIS_DB_HOSTNAME`
and `REDIS_DB_PORT` to NetBox, and Valkey also supplies `REDIS_DB_USERNAME` and
`REDIS_DB_PASSWORD`, resolved through the provider's Juju secrets. The tasks and
caching databases remain 0 and 1. TLS-enabled Valkey connections are not supported.

If neither integration is present, or if both are present at the same time, the
charm is blocked until only one remains.

## Custom certificate trust

The optional `certificates` endpoint (`tls-certificates` interface) requests a
certificate for the NetBox application and adds its CA to the workload's system
CA bundle. All workload processes use the combined bundle through
`REQUESTS_CA_BUNDLE` and `SSL_CERT_FILE`. Removing the relation removes the custom
bundle and restores system trust.
