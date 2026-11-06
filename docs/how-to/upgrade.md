# How to upgrade

**Important:** Before upgrading, make sure to back up your PostgreSQL database. You can check how to backup in [the PostgreSQL charm documentation](https://canonical.com/data/postgresql/docs/14/how-to/back-up-and-restore/).

NetBox supports direct upgrades to any newer release with one exception: major version upgrades. You must be on the latest minor release of your current version before upgrading to the next major version.

## Upgrading to the Ubuntu 26.04 charm

This release moves the charm and rock to Ubuntu 26.04. The charm base cannot change
with `juju refresh`, so deploy the new charm alongside the existing one and migrate
your data. Also note:

* The OCI resource is renamed from `django-app-image` to `app-image`.
* The `redis` integration is still supported. The new `valkey_netbox` integration
  can be used instead, but exactly one of the two must be integrated.

## Minor version upgrade 

To refresh the charm within the current channel (e.g., getting the latest patch or minor version):

```
juju refresh netbox-k8s
```

## Major version upgrade

To upgrade to a new major version, switch the charm channel:

```
juju refresh netbox-k8s --channel=5/stable
```

**Note:** The charm handles the migration logic automatically by renaming the upstream `upgrade.sh` file to `migrate.sh`. This allows the 12-factor framework to execute the script during the charm refresh, ensuring the database is migrated before the service restarts.
