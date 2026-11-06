# How to upgrade

**Important:** Before upgrading, make sure to back up your PostgreSQL database. You can check how to backup in [the PostgreSQL charm documentation](https://canonical.com/data/postgresql/docs/16/how-to/back-up-and-restore/).

NetBox supports direct upgrades to any newer release with one exception: major version upgrades. You must be on the latest minor release of your current version before upgrading to the next major version.

## Migrating from NetBox 4.6 to 4.7

This release upgrades NetBox from 4.6 to 4.7 and moves the charm and rock to
Ubuntu 26.04. Before migrating:

* PostgreSQL 16 is required. NetBox 4.7 does not support earlier PostgreSQL versions.
  Upgrade or migrate your `postgresql-k8s` deployment to channel `16` first.
* The base is now `ubuntu@26.04`.
* Redis is replaced by Valkey. Deploy `valkey` and integrate it using
  `juju integrate valkey netbox-k8s:valkey_netbox`.
* The OCI resource is now named `app-image` instead of `django-app-image`.

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
