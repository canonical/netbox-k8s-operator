# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the NetBox charm."""

import pathlib

from ops import testing

from charm import NetboxCharm

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent


EXPECTED_ENV = {
    "DJANGO_ALLOWED_HOSTS": '["netbox.test-model"]',
    "DJANGO_BASE_URL": "http://netbox.test-model:8000",
    "DJANGO_DEBUG": "false",
    "DJANGO_PEER_FQDNS": "netbox-0.netbox-endpoints.test-model.svc.cluster.local",
    "DJANGO_SECRET_KEY": "test",
    "DJANGO_SAML_USERNAME": "name",
    "POSTGRESQL_DB_CONNECT_STRING": "postgresql://test-username:test-password@"
    "test-postgresql:5432/django-k8s",
    "POSTGRESQL_DB_FRAGMENT": "",
    "POSTGRESQL_DB_NETLOC": "test-username:test-password@test-postgresql:5432",
    "POSTGRESQL_DB_PATH": "/django-k8s",
    "POSTGRESQL_DB_PORT": "5432",
    "POSTGRESQL_DB_QUERY": "",
    "POSTGRESQL_DB_PARAMS": "",
    "POSTGRESQL_DB_SCHEME": "postgresql",
    "POSTGRESQL_DB_HOSTNAME": "test-postgresql",
    "POSTGRESQL_DB_PASSWORD": "test-password",
    "POSTGRESQL_DB_USERNAME": "test-username",
    "POSTGRESQL_DB_NAME": "django-k8s",
    "REDIS_DB_CONNECT_STRING": "redis://redis-hostname:6379",
    "REDIS_DB_FRAGMENT": "",
    "REDIS_DB_HOSTNAME": "redis-hostname",
    "REDIS_DB_NETLOC": "redis-hostname:6379",
    "REDIS_DB_PARAMS": "",
    "REDIS_DB_PATH": "",
    "REDIS_DB_PORT": "6379",
    "REDIS_DB_QUERY": "",
    "REDIS_DB_SCHEME": "redis",
    "S3_ACCESS_KEY": "test-access-key",
    "S3_ADDRESSING_STYLE": "path",
    "S3_BUCKET": "netboxbucket",
    "S3_ENDPOINT": "http://s3-endpoint:9000",
    "S3_PATH": "/",
    "S3_REGION": "us-east-1",
    "S3_SECRET_KEY": "test-secret-key",
    "S3_URI_STYLE": "path",
}


def test_netbox_config(base_state: dict) -> None:
    """
    arrange: set the workload charm config.
    act: start the workload charm and integrate with oauth.
    assert: workload charm should be blocked before the ingress integration and active after.
    """
    state = testing.State(**base_state)
    context = testing.Context(
        charm_type=NetboxCharm,
    )
    out = context.run(context.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus()

    springboot_layer = list(out.containers)[0].plan.services["django"].to_dict()
    assert springboot_layer == {
        "environment": EXPECTED_ENV,
        "startup": "enabled",
        "override": "replace",
        "command": (
            "/bin/python3 -m gunicorn -c /django/gunicorn.conf.py django_app.wsgi:application "
            "-k [ sync ]"
        ),
    }
