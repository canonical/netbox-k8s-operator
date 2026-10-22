# Charm architecture

The NetBox K8s charm initial version has been generated with the help of
the [paas-charm](https://github.com/canonical/paas-charm/)
project. [The paas-charm](https://github.com/canonical/paas-charm/)
project provides many of the functionalities needed by this charm like:
- PostgreSQL integration
- Redis integration
- Django migrations
- Ingress integration
- COS (Prometheus metrics and Loki logs for `gunicorn`).
- OIDC integration.
- S3 integration.

For the static assets, `gunicorn` is used with the help of the [WhiteNoiseMiddleware](https://whitenoise.readthedocs.io/en/stable/index.html).

There is only one container for each unit of NetBox K8s that runs the following
services managed by Pebble:
- `django`: runs `gunicorn`.
- `cron-scheduler`: runs `housekeeping` daily and `syncdatasource` every five minutes
  using Supercronic on unit zero. The existing service name is retained for
  upgrades, but Ubuntu `cron` is no longer installed. Pebble, the scheduler, and
  its jobs run as `_daemon_` without elevated privileges or system PID files.
  The charm supplies the Django environment to the scheduler, and commands
  inherit it while running in `/app`. Schedules use UTC: housekeeping runs at
  midnight and data source synchronization runs every five minutes. Each job
  runs at most once concurrently. Supercronic is built from its pinned upstream
  release, and the schedules are installed at `/etc/netbox/crontab`. Schedule
  directories use mode `0755` and the file uses `0644`, so `_daemon_` can read it. Command
  output and failures go directly to Pebble logs, and a failed command does not
  prevent later scheduled runs. Supercronic waits for active jobs on shutdown.
- `statsd_exporter`: exposes `gunicorn` metrics.

The NetBox K8s charm is designed for a high availability (HA) environment.
The NetBox application can be scaled to more than one unit to provide
HA. See [Configure Scripts and Reports for
HA](../how-to/configure-scripts-reports.md) for the requirements to
use scripts and reports in HA configuration.
