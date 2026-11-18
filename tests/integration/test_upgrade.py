# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the upgrade from NetBox 4.6 to NetBox 4.7.

NetBox 4.7 requires PostgreSQL 15 or later. The upgrade follows the documented procedure:
move the data to a newer PostgreSQL while still running NetBox 4.6, and then refresh the charm.
"""

import logging
import secrets
import string
from collections.abc import Generator

import jubilant
import pytest
import requests

from tests.integration.helpers import (
    create_site,
    get_base_url,
    get_netbox_version,
    get_new_admin_token,
    migrate_postgresql_data,
    site_exists,
)
from tests.integration.types import App

logger = logging.getLogger(__name__)

# pylint: disable=redefined-outer-name

NETBOX_CHARM_NAME = "netbox-k8s"
NETBOX_APP_NAME = "netbox-upgrade"
# Revision of the NetBox 4.6 charm in 4/edge.
NETBOX_4_6_CHANNEL = "4/edge"
NETBOX_4_6_REVISION = 63
OLD_POSTGRESQL_APP_NAME = "postgresql-14"
NEW_POSTGRESQL_APP_NAME = "postgresql-16"


@pytest.fixture(scope="module", name="site_name")
def site_name_fixture() -> str:
    """Return the name of the site created before the upgrade."""
    return "upgrade-" + "".join(secrets.choice(string.ascii_lowercase) for _ in range(8))


@pytest.fixture(scope="module", name="token")
def token_fixture(juju: jubilant.Juju, netbox_4_6: App) -> str:
    """Create an admin token on NetBox 4.6, which must keep working after the upgrade."""
    return get_new_admin_token(juju, netbox_4_6, get_base_url(juju, netbox_4_6.name))


@pytest.fixture(scope="module", name="old_postgresql")
def old_postgresql_fixture(juju: jubilant.Juju) -> Generator[App, None, None]:
    """Deploy PostgreSQL 14, which NetBox 4.7 no longer supports."""
    juju.deploy(
        "postgresql-k8s",
        OLD_POSTGRESQL_APP_NAME,
        channel="14/stable",
        base="ubuntu@22.04",
        config={"profile": "testing"},
        trust=True,
        force=juju.version().major >= 4,
    )
    yield App(OLD_POSTGRESQL_APP_NAME)
    juju.remove_application(OLD_POSTGRESQL_APP_NAME, force=True, destroy_storage=True)


@pytest.fixture(scope="module", name="new_postgresql")
def new_postgresql_fixture(juju: jubilant.Juju) -> Generator[App, None, None]:
    """Deploy PostgreSQL 16."""
    juju.deploy(
        "postgresql-k8s",
        NEW_POSTGRESQL_APP_NAME,
        channel="16/edge" if juju.version().major >= 4 else "16/stable",
        base="ubuntu@24.04",
        config={"profile": "testing"},
        trust=True,
        force=juju.version().major >= 4,
    )
    yield App(NEW_POSTGRESQL_APP_NAME)
    juju.remove_application(NEW_POSTGRESQL_APP_NAME, force=True, destroy_storage=True)


@pytest.fixture(scope="module", name="netbox_4_6")
def netbox_4_6_fixture(
    juju: jubilant.Juju,
    old_postgresql: App,
    valkey_app: App,
    s3_integrator_app: App,
) -> Generator[App, None, None]:
    """Deploy the NetBox 4.6 charm from Charmhub, integrated with PostgreSQL 14."""
    juju.deploy(
        NETBOX_CHARM_NAME,
        NETBOX_APP_NAME,
        channel=NETBOX_4_6_CHANNEL,
        revision=NETBOX_4_6_REVISION,
        base="ubuntu@26.04",
        config={"django-debug": False, "django-allowed-hosts": "*"},
    )
    juju.integrate(f"{NETBOX_APP_NAME}:postgresql", old_postgresql.name)
    juju.integrate(f"{NETBOX_APP_NAME}:valkey", valkey_app.name)
    juju.integrate(f"{NETBOX_APP_NAME}:s3", s3_integrator_app.name)
    juju.wait(
        lambda status: jubilant.all_active(
            status,
            NETBOX_APP_NAME,
            old_postgresql.name,
            valkey_app.name,
            s3_integrator_app.name,
        ),
        timeout=20 * 60,
    )
    yield App(NETBOX_APP_NAME)
    juju.remove_application(NETBOX_APP_NAME, force=True, destroy_storage=True)


def test_netbox_4_6_baseline(
    juju: jubilant.Juju, netbox_4_6: App, token: str, site_name: str
) -> None:
    """
    arrange: Deploy NetBox 4.6 from Charmhub on PostgreSQL 14.
    act: Create a site through the API.
    assert: NetBox reports a 4.6 version and the site exists.
    """
    base_url = get_base_url(juju, netbox_4_6.name)
    assert get_netbox_version(base_url).startswith("4.6.")

    create_site(base_url, token, site_name)

    assert site_exists(base_url, token, site_name)


def test_move_to_postgresql_16(
    juju: jubilant.Juju,
    netbox_4_6: App,
    old_postgresql: App,
    new_postgresql: App,
    token: str,
    site_name: str,
) -> None:
    """
    arrange: Run NetBox 4.6 on PostgreSQL 14, with data, and deploy PostgreSQL 16.
    act: Dump the database, point NetBox at PostgreSQL 16 and restore the dump.
    assert: NetBox 4.6 is active and still has the data.
    """
    juju.wait(lambda status: jubilant.all_active(status, new_postgresql.name), timeout=20 * 60)

    juju.remove_relation(f"{netbox_4_6.name}:postgresql", old_postgresql.name)
    juju.wait(lambda status: status.apps[netbox_4_6.name].is_blocked, timeout=10 * 60)
    juju.integrate(f"{netbox_4_6.name}:postgresql", new_postgresql.name)
    # NetBox creates an empty schema in the new database before the data is restored over it.
    juju.wait(
        lambda status: jubilant.all_active(status, netbox_4_6.name, new_postgresql.name),
        timeout=20 * 60,
    )

    # The old database is kept, as the dump is read from it.
    migrate_postgresql_data(juju, netbox_4_6.name, old_postgresql.name, new_postgresql.name)

    assert site_exists(get_base_url(juju, netbox_4_6.name), token, site_name)


def test_refresh_to_netbox_4_7(
    juju: jubilant.Juju,
    netbox_4_6: App,
    netbox_charm: str,
    netbox_app_image: str,
    token: str,
    site_name: str,
) -> None:
    """
    arrange: Run NetBox 4.6 on PostgreSQL 16, with data.
    act: Refresh the charm to the locally built charm and NetBox 4.7 image.
    assert: NetBox is active, reports 4.7, keeps the data and the token, and runs a worker.
    """
    juju.refresh(
        netbox_4_6.name,
        path=netbox_charm,
        resources={"app-image": netbox_app_image},
    )
    juju.wait(
        lambda status: (
            status.apps[netbox_4_6.name].charm.startswith("local:")
            and jubilant.all_active(status, netbox_4_6.name)
        ),
        timeout=30 * 60,
    )

    status = juju.status()
    for unit in status.apps[netbox_4_6.name].units.values():
        base_url = f"http://{unit.address}:8000"
        res = requests.get(f"{base_url}/api/status/", timeout=20)
        assert res.status_code == 200
        assert res.json()["netbox-version"].startswith("4.7.")
        assert res.json()["rq-workers-running"] == 1

        res = requests.get(base_url, timeout=20)
        assert res.status_code == 200
        assert b"<title>Home | NetBox</title>" in res.content

        assert site_exists(base_url, token, site_name)
