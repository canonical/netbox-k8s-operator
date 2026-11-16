# How to migrate to the Ubuntu 26.04 LTS charm and Valkey

The Ubuntu 26.04 LTS release of the NetBox charm changes the charm base to
`ubuntu@26.04`, renames the OCI resource from `django-app-image` to `app-image`,
and adds the `valkey` integration as the replacement for `redis`.
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

```{important}
The 26.04 charm renames the workload container from `django-app` to `app`, and
Juju 3.x and 4.0 do not remove the old container on refresh (see
[LP#1991955](https://bugs.launchpad.net/juju/+bug/1991955)), which leaves the
unit in `error`. On those versions, either apply the workaround in the note
below or skip the refresh and follow
[Redeploy instead of refreshing (Juju 3.x and 4.0)](#redeploy-instead-of-refreshing-juju-3x-and-40).
```

Refresh in place and pass the new base.

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
In testing with a locally built charm, Juju kept the old `django-app` container
in the pod next to the new `app` container. The old container crash-loops with
`cannot listen on ":38813": address already in use`, because both Pebble
instances share the pod network, and the unit goes into `error`. Remove the old
container from the StatefulSet:

    kubectl get sts netbox-k8s -n <model> -o jsonpath='{range .spec.template.spec.containers[*]}{.name}{"\n"}{end}'
    kubectl patch sts netbox-k8s -n <model> --type=json \
      -p='[{"op":"remove","path":"/spec/template/spec/containers/<index of django-app>"}]'

The pod then restarts with two containers (`charm` and `app`).
```

### Redeploy instead of refreshing (Juju 3.x and 4.0)

On Juju 3.x and 4.0, remove the application and deploy it again on the new
base. The PostgreSQL, S3 and other integrated applications stay in the model,
so NetBox keeps its data when it is integrated again.

1. Remove the NetBox application and wait until it is gone:

   ```bash
   juju remove-application netbox-k8s
   juju status --watch 5s
   ```

2. Deploy the new charm on `ubuntu@26.04`:

   ```bash
   juju deploy netbox-k8s --channel 4/edge --base ubuntu@26.04
   ```

   For a locally built charm, pass the new resource name:

   ```bash
   juju deploy ./netbox-k8s_amd64.charm --base ubuntu@26.04 \
     --resource app-image=localhost:32000/netbox:latest
   ```

3. Add back every integration the application had. The required ones are
   `postgresql` and `s3`, plus one cache integration (`valkey` or `redis`):

   ```bash
   juju integrate netbox-k8s:postgresql postgresql-k8s
   juju integrate netbox-k8s:s3 s3-integrator
   juju integrate netbox-k8s:valkey valkey:valkey-client
   ```

   Add the optional ones you used before, for example:

   ```bash
   juju integrate netbox-k8s:oidc oauth-external-idp-integrator
   juju integrate netbox-k8s:saml saml-integrator
   juju integrate netbox-k8s:certificates self-signed-certificates
   ```

4. Re-apply any configuration you had set with `juju config`, since removing
   the application discards it.

If you deploy with the `valkey` integration in step 3, you have already
completed the Redis to Valkey switch, and you only need step 3 of the next
section to remove the old Redis application.

### Replace Redis with Valkey

1. Deploy Valkey and wait until it is `active`:

   ```bash
   juju deploy valkey --channel 9/edge --trust
   juju wait-for application valkey --query='status=="active"'
   ```

2. Remove the Redis integration and add the Valkey integration:

   ```bash
   juju remove-relation netbox-k8s redis-k8s
   juju integrate netbox-k8s:valkey valkey:valkey-client
   ```

3. When NetBox is `active`, remove Redis:

   ```bash
   juju remove-application redis-k8s
   ```

Between steps 2 and 3, and until Valkey has finished starting, NetBox is
`blocked` (`missing integrations: valkey` or
`Valkey relation data is not ready`). This is expected and clears by itself.
Wait for Valkey to be `active` before you remove the Redis integration to keep
the blocked period short.

NetBox gets the new `VALKEY_DB_HOSTNAME`, `VALKEY_DB_PORT`, `VALKEY_DB_USERNAME`
and `VALKEY_DB_PASSWORD` values from the Valkey relation. To check, run
`pebble plan` in the `app` container.

## Migration with Terraform

The `terraform/product` module changes as follows:

* The `redis_k8s` variable and the `redis-k8s` module are removed. Setting
  `redis_k8s` now fails validation with a message that points to this guide.
* A new `valkey` variable is added. The product module uses the Terraform charm
  module published in the
  [Valkey operator repository](https://github.com/canonical/valkey-operator/tree/9/edge/terraform/charm)
  with the `9/edge` channel, base `ubuntu@26.04` and `trust` enabled. The
  `netbox_k8s` and `valkey` variables can be left empty (`{}`) to use defaults.
* All modules require the Juju Terraform provider 2.2.1 or later, as the
  Valkey module does.
* The `juju_integration.netbox_redis` resource is replaced with
  `juju_integration.netbox_valkey`, which connects `valkey` with
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

* On Juju 3.x and 4.0, the old `django-app` container is not removed on refresh
  ([LP#1991955](https://bugs.launchpad.net/juju/+bug/1991955)). Set
  `netbox_k8s = { base = "ubuntu@26.04" }` and have Terraform replace the
  application (for example with
  `terraform apply -replace=module.netbox_k8s.juju_application.netbox_k8s`),
  or remove and redeploy manually as described above. The integrations are
  re-created by the module, and PostgreSQL keeps the data.

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
