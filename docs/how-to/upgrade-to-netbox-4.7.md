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

The following steps move the data to a new PostgreSQL 16 application, and the old
`postgresql-k8s` application is kept until you have verified the result. Replace the
application names with yours.

1. Deploy PostgreSQL 16:

   ```
   juju deploy postgresql-k8s postgresql-16 --channel 16/stable --trust
   juju wait-for application postgresql-16
   ```

1. Stop changes to NetBox, for example by asking your users to stop working. Then dump the
   database from the old PostgreSQL. The PostgreSQL 16 client tools can read a PostgreSQL 14
   server, so run the dump on the new unit:

   ```
   juju run postgresql-k8s/leader get-password username=operator
   juju ssh --container postgresql postgresql-16/0
   ```

   In the shell on the new unit, replace the placeholders with the password from the previous
   command, the address of the old PostgreSQL unit and the NetBox database name. The name
   is the NetBox application name, `netbox-k8s` by default:

   ```
   PGPASSWORD=<operator password> pg_dump --format=custom --no-owner --no-privileges \
       --host=<old unit address> --username=operator --dbname=netbox-k8s \
       --file=/tmp/netbox.dump
   ```

1. Replace the PostgreSQL integration. NetBox 4.6 creates an empty schema in the new database:

   ```
   juju remove-relation netbox-k8s postgresql-k8s
   juju integrate netbox-k8s:postgresql postgresql-16
   juju wait-for application netbox-k8s
   ```

1. Restore the dump into the new database as the NetBox database user. The credentials of the
   user are in the environment of the `django` service in the NetBox container:

   ```
   juju ssh --container app netbox-k8s/0 /charm/bin/pebble plan
   ```

   Use the values of `POSTGRESQL_DB_USERNAME`, `POSTGRESQL_DB_PASSWORD`,
   `POSTGRESQL_DB_HOSTNAME` and `POSTGRESQL_DB_NAME` to restore the dump on the
   `postgresql-16/0` unit. The extensions already exist in the new database, so skip them:

   ```
   pg_restore --list /tmp/netbox.dump | grep -v EXTENSION > /tmp/netbox.list
   pg_restore --clean --if-exists --no-owner --no-privileges --exit-on-error \
       --use-list=/tmp/netbox.list \
       --dbname=postgresql://<user>:<password>@<hostname>:5432/<database> /tmp/netbox.dump
   rm /tmp/netbox.dump /tmp/netbox.list
   ```

1. Check that NetBox is active and that your data is present. Keep the old PostgreSQL
   application until you are sure that you don't need it.

## Refresh the charm

NetBox 4.7 is published to the `4.7` track, so switch the charm channel and check the result:

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
  enqueued before the upgrade fail after it.
