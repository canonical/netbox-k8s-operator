# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helper functions for integration tests."""

import secrets
import shlex
import string
from urllib.parse import quote

import jubilant
import requests
import yaml

from tests.integration.types import App


def get_new_admin_token(juju: jubilant.Juju, netbox_app: App, netbox_base_url: str) -> str:
    """Create an admin token for NetBox.

    Args:
        juju: Juju instance.
        netbox_app: NetBox app. Necessary to create the superuser
        netbox_base_url: NetBox base url. Needed to get token from superuser.

    Returns:
        The new admin token
    """
    # Create a superuser
    username = "".join((secrets.choice(string.ascii_letters) for i in range(8)))
    action_create_user = juju.run(
        f"{netbox_app.name}/0",
        "create-superuser",
        {"username": username, "email": "admin@example.com"},
    )
    assert action_create_user.status == "completed"
    password = action_create_user.results["password"]

    # Request a v1 token to match the callers' Token authorization scheme.
    url = f"{netbox_base_url}/api/users/tokens/provision/"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    res = requests.post(
        url,
        json={"username": username, "password": password, "version": 1},
        timeout=5,
        headers=headers,
    )
    assert res.status_code == 201, f"Token provisioning failed: HTTP {res.status_code}"
    token = res.json()["token"]
    return token


def get_base_url(juju: jubilant.Juju, app_name: str) -> str:
    """Get the URL of the first unit of an application.

    Args:
        juju: Juju instance.
        app_name: Name of the application.

    Returns:
        The base URL of the first unit.
    """
    address = juju.status().apps[app_name].units[f"{app_name}/0"].address
    return f"http://{address}:8000"


def auth_headers(token: str) -> dict[str, str]:
    """Build the headers for an authenticated NetBox API request.

    Args:
        token: NetBox API token.

    Returns:
        The request headers.
    """
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"TOKEN {token}",
    }


def get_netbox_version(base_url: str) -> str:
    """Get the NetBox version from the status API.

    Args:
        base_url: NetBox base URL.

    Returns:
        The NetBox version.
    """
    res = requests.get(f"{base_url}/api/status/", timeout=20)
    assert res.status_code == 200
    return res.json()["netbox-version"]


def create_site(base_url: str, token: str, name: str) -> None:
    """Create a site through the NetBox API.

    Args:
        base_url: NetBox base URL.
        token: NetBox API token.
        name: Name and slug of the site.
    """
    res = requests.post(
        f"{base_url}/api/dcim/sites/",
        json={"name": name, "slug": name},
        timeout=20,
        headers=auth_headers(token),
    )
    assert res.status_code == 201, f"Site creation failed: HTTP {res.status_code}"


def site_exists(base_url: str, token: str, name: str) -> bool:
    """Check if a site exists through the NetBox API.

    Args:
        base_url: NetBox base URL.
        token: NetBox API token.
        name: Slug of the site.

    Returns:
        True if the site exists.
    """
    res = requests.get(
        f"{base_url}/api/dcim/sites/",
        params={"slug": name},
        timeout=20,
        headers=auth_headers(token),
    )
    assert res.status_code == 200
    return res.json()["count"] == 1


def migrate_postgresql_data(
    juju: jubilant.Juju, netbox_app_name: str, source_app_name: str, target_app_name: str
) -> None:
    """Copy the NetBox database from one PostgreSQL application to another.

    The NetBox application must already be integrated with the target PostgreSQL, so that
    the database and the NetBox database user exist there.

    Args:
        juju: Juju instance.
        netbox_app_name: Name of the NetBox application.
        source_app_name: Name of the PostgreSQL application to dump.
        target_app_name: Name of the PostgreSQL application to restore into.
    """
    status = juju.status()
    source_host = status.apps[source_app_name].units[f"{source_app_name}/0"].address
    source_password = juju.run(
        f"{source_app_name}/leader", "get-password", {"username": "operator"}
    ).results["password"]

    plan = yaml.safe_load(
        juju.ssh(f"{netbox_app_name}/0", "/charm/bin/pebble plan", container="app")
    )
    env = plan["services"]["django"]["environment"]
    database = env["POSTGRESQL_DB_NAME"]
    target_uri = (
        f"postgresql://{quote(env['POSTGRESQL_DB_USERNAME'], safe='')}"
        f":{quote(env['POSTGRESQL_DB_PASSWORD'], safe='')}"
        f"@{env['POSTGRESQL_DB_HOSTNAME']}:{env.get('POSTGRESQL_DB_PORT', '5432')}/{database}"
    )

    # The PostgreSQL 16 client tools can dump a PostgreSQL 14 server.
    script = " && ".join(
        [
            f"PGPASSWORD={shlex.quote(source_password)} pg_dump --format=custom --no-owner "
            f"--no-privileges --host={source_host} --username=operator "
            f"--dbname={shlex.quote(database)} --file=/tmp/netbox.dump",
            "pg_restore --list /tmp/netbox.dump | grep -v EXTENSION > /tmp/netbox.list",
            "pg_restore --clean --if-exists --no-owner --no-privileges --exit-on-error "
            f"--use-list=/tmp/netbox.list --dbname={shlex.quote(target_uri)} /tmp/netbox.dump",
            "rm -f /tmp/netbox.dump /tmp/netbox.list",
        ]
    )
    juju.ssh(
        f"{target_app_name}/0",
        f"sh -c {shlex.quote(script)}",
        container="postgresql",
    )
