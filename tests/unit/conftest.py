# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for NetBox operator charm unit tests."""

import os
import pathlib
import textwrap

import pytest
from ops import testing
from ops.testing import Harness

import charm

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent


def postgresql_relation(db_name):
    """Postgresql relation fixture."""
    relation_data = {
        "database": db_name,
        "endpoints": "test-postgresql:5432",
        "password": "test-password",
        "username": "test-username",
    }
    return testing.Relation(
        endpoint="postgresql",
        interface="postgresql_client",
        remote_app_data=relation_data,
    )


@pytest.fixture(scope="function", name="base_state")
def django_base_state_fixture():
    """State with container and config file set."""
    os.chdir(PROJECT_ROOT)
    yield {
        "relations": [
            testing.PeerRelation(
                "secret-storage", local_app_data={"django_secret_key": "test"}
            ),
            testing.Relation(
                endpoint="redis",
                interface="redis",
                id=8,
                local_app_data={},
                local_unit_data={},
                remote_app_name="redis-k8s",
                limit=1,
                remote_app_data={
                    "leader-host": "redis-k8s-0.redis-k8s-endpoints.test-model.svc.cluster.local"
                },
                remote_units_data={0: {"hostname": "redis-hostname", "port": "6379"}},
            ),
            testing.Relation(
                endpoint="s3",
                interface="s3",
                id=6,
                local_app_data={"bucket": "netbox"},
                local_unit_data={},
                remote_app_name="s3-integrator",
                limit=1,
                remote_app_data={
                    "access-key": "test-access-key",
                    "bucket": "netboxbucket",
                    "data": '{"bucket": "netbox"}',
                    "endpoint": "http://s3-endpoint:9000",
                    "path": "/",
                    "region": "us-east-1",
                    "s3-uri-style": "path",
                    "secret-key": "test-secret-key",
                },
                remote_units_data={0: {}},
            ),
            postgresql_relation("django-k8s"),
        ],
        "containers": {
            testing.Container(
                name="django-app",
                can_connect=True,
                mounts={
                    "data": testing.Mount(
                        location="/django/gunicorn.conf.py", source="conf"
                    )
                },
                execs={
                    testing.Exec(
                        command_prefix=["/bin/python3"],
                        return_code=0,
                    ),
                },
                _base_plan={
                    "services": {
                        "django": {
                            "startup": "enabled",
                            "override": "replace",
                            "command": "/bin/python3 -m gunicorn -c /django/gunicorn.conf.py django_app.wsgi:application -k [ sync ]",
                        }
                    }
                },
            )
        },
        "model": testing.Model(name="test-model"),
    }


@pytest.fixture(scope="function", name="harness")
def harness_fixture():
    """Enable ops test framework harness.

    Yields:
       Harness fixture
    """
    # The real configuration files are created by expanding
    # the extension 'django-framework'. However, this is not
    # supported by ops.testing. An alternative to setting it here
    # would be to call `charmcraft expand-extensions`.
    meta_file = textwrap.dedent(
        """\
name: netbox
type: charm
containers:
  django-app:
    resource: django-app-image
peers:
  secret-storage:
    interface: secret-storage
provides:
  grafana-dashboard:
    interface: grafana_dashboard
  metrics-endpoint:
    interface: prometheus_scrape
requires:
  ingress:
    interface: ingress
    limit: 1
  logging:
    interface: loki_push_api
  postgresql:
    interface: postgresql_client
    limit: 1
  redis:
    interface: redis
    limit: 1
  saml:
    interface: saml
    limit: 1
    optional: true
  s3:
    interface: s3
    limit: 1
resources:
  django-app-image:
     type: oci-image
"""
    )

    actions_file = textwrap.dedent(
        """\
    create-superuser:
      email:
        type: string
      username:
        type: string
    rotate-secret-key:
"""
    )

    harness = Harness(charm.NetboxCharm, meta=meta_file, actions=actions_file)

    yield harness

    harness.cleanup()
