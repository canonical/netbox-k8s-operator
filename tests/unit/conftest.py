# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for NetBox operator charm unit tests."""

import os
import pathlib

import pytest
from ops import testing
from ops.testing import PeerRelation, Relation

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent


def peer_relation() -> PeerRelation:
    """Peer relation for NetBox charm.

    Returns:
        Relation: Peer relation object.
    """
    return PeerRelation("secret-storage", local_app_data={"django_secret_key": "test"})


def postgresql_relation() -> Relation:
    """Postgresql relation fixture.

    Returns:
        Relation: Postgresql relation object.
    """
    return Relation(
        endpoint="postgresql",
        interface="postgresql_client",
        remote_app_data={
            "database": "django-k8s",
            "endpoints": "test-postgresql:5432",
            "password": "test-password",
            "username": "test-username",
        },
    )


def redis_relation() -> Relation:
    """Redis relation fixture.

    Returns:
        Relation: Redis relation object.
    """
    return Relation(
        endpoint="redis",
        interface="redis",
        remote_app_name="redis-k8s",
        limit=1,
        remote_app_data={"leader-host": "redis-hostname"},
        remote_units_data={0: {"hostname": "redis-hostname", "port": "6379"}},
    )


def s3_relation() -> Relation:
    """S3 relation fixture.

    Returns:
        Relation: S3 relation object.
    """
    return Relation(
        endpoint="s3",
        interface="s3",
        local_app_data={"bucket": "netbox"},
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
    )


@pytest.fixture(scope="function", name="base_state")
def django_base_state_fixture() -> dict:
    """State with container and config file set."""
    os.chdir(PROJECT_ROOT)
    return {
        "relations": [
            peer_relation(),
            postgresql_relation(),
            redis_relation(),
            s3_relation(),
        ],
        "containers": {
            testing.Container(
                name="django-app",
                can_connect=True,
                mounts={"data": testing.Mount(location="/django/gunicorn.conf.py", source="conf")},
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
                            "command": "/bin/python3 -m gunicorn -c /django/gunicorn.conf.py "
                            "django_app.wsgi:application -k [ sync ]",
                        }
                    }
                },
            )  # type: ignore
        },
        "model": testing.Model(name="test-model"),
    }
