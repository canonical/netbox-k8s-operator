# How to upgrade

**Important**: Before upgrading, make sure to back up your PostgreSQL database.

NetBox supports direct upgrades to any newer release with one exception: major version upgrades. You must be on the latest minor release of your current version before upgrading to the next major version.

## Minor Version Upgrade 

To refresh the charm within the current channel (e.g., getting the latest patch or minor version):

```
juju refresh netbox-k8s
```

## Major Version Upgrade

To upgrade to a new major version, switch the charm channel:

```
juju refresh netbox-k8s --channel=5/stable
```

..Note: The charm handles the migration logic automatically by renaming the upstream `upgrade.sh` file to `migrate.sh`. This allows the 12-factor framework to execute the script during the charm refresh, ensuring the database is migrated before the service restarts.
