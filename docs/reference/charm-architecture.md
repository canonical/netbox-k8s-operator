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
  using Ubuntu's `cron` on unit zero. The daemon runs with UID and GID zero to
  manage its PID file and system schedules. The rock includes Ubuntu's base
  account data so `cron` can resolve the root account in its schedules.
  Jobs use Pebble to run as `_daemon_` in `/app` with
  the Django service environment, and send output to Pebble logs for the scheduler.
- `statsd_exporter`: exposes `gunicorn` metrics.

The NetBox K8s charm is designed for a high availability (HA) environment.
The NetBox application can be scaled to more than one unit to provide
HA. See [Configure Scripts and Reports for
HA](../how-to/configure-scripts-reports.md) for the requirements to
use scripts and reports in HA configuration.
