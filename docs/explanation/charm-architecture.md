# NetBox charm architecture

The NetBox charm initial version has been generated with the help of
the [paas-app-charmer](https://github.com/canonical/paas-app-charmer/)
project. [The paas-app-charmer](https://github.com/canonical/paas-app-charmer/)
project provides many of the functionalities needed by this charm like:
- PostgreSQL integration
- Redis integration
- Django migrations
- Ingress integration
- COS (Prometheus metrics and Loki logs for gunicorn).

For the static assets, gunicorn is used with the help of the [WhiteNoiseMiddleware](https://whitenoise.readthedocs.io/en/stable/index.html).

There is only one container for each unit of NetBox that runs the following
services managed by Pebble:
- django. Runs gunicorn.
- cron. Cron service that runs management commands for housekeeping and syncdatasource.
- statsd_exporter. To expose gunicorn metrics.

Besides the integrations provided directly by the paas-app-charmer toolchain, the following
integrations are implemented in NetBox:
- SAML integration.
- S3 integration.

The NetBox charm is designed for a high availability (HA) environment.
The NetBox application can be scaled to more than one unit to provide
HA. See [Configure Scripts and Reports for
HA](../how-to/configure-scripts-reports.md) for the requirements to
use scripts and reports in HA configuration.