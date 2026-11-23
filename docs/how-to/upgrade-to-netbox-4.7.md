# How to upgrade to NetBox 4.7

NetBox 4.7 requires **PostgreSQL 15 or later**. PostgreSQL 14 is no longer supported.
The PostgreSQL charm cannot upgrade a PostgreSQL 14 deployment to a newer major version in place,
so you must move your data to a new PostgreSQL deployment first.

The upgrade has two parts:

1. Move the NetBox database to PostgreSQL 15 or later, while NetBox is still on 4.6.
1. Refresh `netbox-k8s` to the NetBox 4.7 charm.

```{important}
Back up your PostgreSQL database before you start. See
[the PostgreSQL charm documentation](https://canonical.com/data/postgresql/docs/16/how-to/back-up-and-restore/).
```

## Check your PostgreSQL version

If your deployment already uses PostgreSQL 15 or later, skip to
[Refresh the charm](#refresh-the-charm).

To check the version, run `juju status postgresql-k8s`. The version is shown in the
`Version` column.

The charm doesn't check the PostgreSQL version. Make sure that the version is at least 15
before you refresh.

## Upgrade requirements

* PostgreSQL 15 or later. The NetBox database user needs the `CREATE` privilege on the
  database, because NetBox 4.7 creates the `ltree` extension that ships with PostgreSQL.
  The database user created through the `postgresql` integration normally satisfies this.
* Redis or Valkey 6.0 or later.
* Plan for a longer upgrade on large databases. NetBox 4.7 migrates hierarchical models to
  `ltree` and rebuilds the config context cache, and the migration locks tables while it runs.
  These migrations can't be reversed in practice.

## Move the database to PostgreSQL 16

Follow the PostgreSQL charm guide to
[migrate data from PostgreSQL 14 to 16](https://canonical.com/data/postgresql/docs/16/how-to/data-migration/migrate-data-from-14-to-16/),
while NetBox is still on 4.6. Then integrate `netbox-k8s` with the new PostgreSQL
application, check that NetBox is active and that your data is present. Keep the old
PostgreSQL application until you are sure that you don't need it.

## Refresh the charm

NetBox 4.7 is published to the `4.7` track and requires the Ubuntu 26.04 LTS charm base.
If your NetBox 4.6 application still uses an older base, first follow
[Migrate to the Ubuntu 26.04 LTS charm and Valkey](migrate-to-26.04-and-valkey.md)
while staying on the `4` track, including the Juju-version-specific refresh or redeploy
procedure. Once NetBox 4.6 is active on `ubuntu@26.04`, switch the charm channel and check the result:

```
juju refresh netbox-k8s --channel 4.7/edge
juju status netbox-k8s
```

Use `4.7/stable` once it is promoted. The `4` track stays on NetBox 4.6.

The charm runs the NetBox migrations during the refresh. Don't remove the old PostgreSQL
until NetBox 4.7 is active.

## Other breaking changes

Read the
[NetBox 4.7 release notes](https://github.com/netbox-community/netbox/releases/tag/v4.7.0)
before you upgrade. These changes can affect your scripts, plugins and integrations:

* The REST API returns selection custom field values as objects and returns structured errors
  for failed bulk operations.
* Config context data is always included in the REST API representations of devices and
  virtual machines.
* The `housekeeping` management command is removed. NetBox runs housekeeping as a system
  job in the worker, and the charm no longer schedules the command.
* Services use a `port_mappings` field. The `protocol` and `ports` fields are deprecated.
* Single sign-on uses `social-auth-app-django` 6.0. Test authentication on a non-production
  deployment first.
* Wait for the background queues to drain before you refresh, because webhook jobs that were
  queued before the upgrade fail after it.
