# How to migrate to the Ubuntu 26.04 charm and Valkey

The Ubuntu 26.04 release of the NetBox charm changes the charm base to
`ubuntu@26.04`, renames the OCI resource from `django-app-image` to `app-image`,
and adds the `valkey_netbox` integration as the replacement for `redis`.
NetBox needs exactly one cache integration, so you must switch from Redis to
Valkey, or keep Redis and only change the base.

**Important:** Back up your PostgreSQL database before you start. See
[the PostgreSQL charm documentation](https://canonical.com/data/postgresql/docs/14/how-to/back-up-and-restore/).

The migration has two parts, which can be done together:

1. Refresh `netbox-k8s` to the new charm and base.
2. Replace the Redis integration with a Valkey integration.

Follow the section that matches how you manage your deployment.

## Manual migration with Juju

### Refresh the charm and base

Refresh in place and pass the new base. You don't need to deploy a second
application next to the existing one.

```bash
juju refresh netbox-k8s --channel 4/edge --base ubuntu@26.04
```

For a locally built charm, also pass the new resource name:

```bash
juju refresh netbox-k8s --path ./netbox-k8s_amd64.charm --base ubuntu@26.04 \
  --resource app-image=localhost:32000/netbox:latest
```

The unit is replaced and goes through `maintenance` while the pod restarts.

```{note}
Juju keeps the old `django-app` container in the pod next to the new `app`
container. The old container crash-loops with
`cannot listen on ":38813": address already in use`, because both Pebble
instances share the pod network, and the unit goes into `error`. Remove the old
container from the StatefulSet:

    kubectl get sts netbox-k8s -n <model> -o jsonpath='{range .spec.template.spec.containers[*]}{.name}{"\n"}{end}'
    kubectl patch sts netbox-k8s -n <model> --type=json \
      -p='[{"op":"remove","path":"/spec/template/spec/containers/<index of django-app>"}]'

The pod then restarts with two containers (`charm` and `app`).
```

### Replace Redis with Valkey

1. Deploy Valkey and wait until it is `active`:

   ```bash
   juju deploy valkey --channel 9/edge --trust
   juju wait-for application valkey --query='status=="active"'
   ```

2. Remove the Redis integration and add the Valkey integration:

   ```bash
   juju remove-relation netbox-k8s redis-k8s
   juju integrate netbox-k8s:valkey_netbox valkey:valkey-client
   ```

3. When NetBox is `active`, remove Redis:

   ```bash
   juju remove-application redis-k8s
   ```

Between steps 2 and 3, and until Valkey has finished starting, NetBox is
`blocked` (`missing integrations: valkey_netbox` or
`Valkey relation data is not ready`). This is expected and clears by itself.
Wait for Valkey to be `active` before you remove the Redis integration to keep
the blocked period short.

NetBox gets the new `REDIS_DB_HOSTNAME`, `REDIS_DB_PORT`, `REDIS_DB_USERNAME`
and `REDIS_DB_PASSWORD` values from the Valkey relation. To check, run
`pebble plan` in the `app` container.

## Migration with Terraform

The `terraform/product` module changes as follows:

* The `redis_k8s` variable and the `redis-k8s` module are removed.
* A new `valkey` variable and `valkey` module are added. They default to the
  `9/edge` channel, base `ubuntu@26.04`, with `trust` enabled. The
  `netbox_k8s` and `valkey` variables can be left empty (`{}`) to use defaults.
* The `juju_integration.netbox_redis` resource is replaced with
  `juju_integration.netbox_valkey`, which connects `valkey_netbox` with
  `valkey-client`.
* The default base of `netbox_k8s` is `ubuntu@26.04`.

To migrate:

1. Remove `redis_k8s = { ... }` from your variables and add, if you want to
   change anything from the defaults:

   ```hcl
   netbox_k8s = {
     channel = "4/edge"
     base    = "ubuntu@26.04"
   }
   valkey = {}
   ```

2. Review the plan. You should see the base change in place on `netbox-k8s`,
   the new `valkey` application and integration, and the destruction of the
   Redis application and integration:

   ```bash
   terraform plan -var-file=your.tfvars
   ```

3. Apply:

   ```bash
   terraform apply -var-file=your.tfvars
   ```

Notes:

* The provider can't deploy or refresh local charms (it fails with
  `unknown schema for charm URL "local:..."`). The Terraform path only works
  with a charm published to Charmhub.
* Terraform applies the Valkey integration as soon as the application exists,
  so NetBox is `blocked` until Valkey finishes starting.
* The `juju_application` for `netbox-k8s`, `s3-integrator` and
  `oauth-external-idp-integrator` own their `config`. An empty `config = {}`
  resets any option you set with `juju config`, so keep options such as the S3
  endpoint and bucket in your variables.
* The container leftover described above also applies. If the unit goes into
  `error` after the refresh, remove the old `django-app` container as shown in
  the manual migration.
