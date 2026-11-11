# Integrations

See [Integrations](https://charmhub.io/netbox-k8s/integrations).

## Cache

NetBox needs exactly one cache integration: `redis` (`redis` interface) or
`valkey` (`valkey_client` interface). Redis supplies `REDIS_DB_HOSTNAME` and
`REDIS_DB_PORT`, and Valkey supplies `VALKEY_DB_HOSTNAME`, `VALKEY_DB_PORT`,
`VALKEY_DB_USERNAME` and `VALKEY_DB_PASSWORD`, resolved through the provider's Juju
secrets. NetBox reads whichever set is present. The tasks and caching databases
remain 0 and 1. TLS-enabled Valkey connections are not supported.

If neither integration is present, the charm is blocked and reports `valkey`
as missing. If both are present at the same time, the charm is blocked until only
one remains.

## Custom certificate trust

The optional `certificates` endpoint (`tls-certificates` interface) requests a
certificate for the NetBox application and adds its CA to the workload's system
CA bundle. All workload processes use the combined bundle through
`REQUESTS_CA_BUNDLE` and `SSL_CERT_FILE`. Removing the relation removes the custom
bundle and restores system trust.
