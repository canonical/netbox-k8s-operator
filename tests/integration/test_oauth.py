# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Oauth Integration."""

import json
import logging
import re
import time
from urllib.parse import urlparse

import jubilant
import pytest
import requests
from playwright.sync_api import expect, sync_playwright

from tests.integration.types import App

logger = logging.getLogger(__name__)


# Pylint thinks there are too many local variables, but that's not true.
# pylint: disable=too-many-locals, unused-argument


@pytest.mark.usefixtures("identity_bundle")
@pytest.mark.usefixtures("browser_context_manager")
def test_oauth_integrations(
    juju: jubilant.Juju,
    netbox_app: App,
    http: requests.Session,
):
    """
    arrange: set up the test Juju model and deploy the NetBox charm.
    act: integrate with ingress and hydra.
    assert: the NetBox charm uses the Kratos charm as the idp.
    """
    endpoint = "login"
    test_email = "test@example.com"
    test_password = "Testing1"
    test_username = "admin"
    test_secret = "secret_password"

    app = netbox_app
    status = juju.status()

    # mypy things status.apps is possibly None, but if it's None, something is very wrong
    if not status.apps.get(app.name).relations.get("ingress"):  # type: ignore
        juju.integrate(f"{app.name}", "traefik-public")

    juju.wait(
        jubilant.all_active,
        timeout=15 * 60,
        delay=5,
    )

    # Integrate with self-signed-certificates so NetBox trusts the CA used by Traefik/Hydra.
    # This must happen before the OIDC integration so the CA bundle is available when NetBox
    # makes server-side HTTPS calls to Hydra's token endpoint.
    if not status.apps.get(app.name).relations.get("receive-ca-cert"):  # type: ignore
        juju.integrate(
            f"{app.name}:receive-ca-cert", "self-signed-certificates:send-ca-cert"
        )

    juju.wait(
        jubilant.all_active,
        timeout=10 * 60,
        delay=5,
    )

    # Wait for the CA certificate to actually be pushed to the container.
    # The certificate_transfer relation may fire relation-changed before the provider
    # has written the certificate data, so we poll until the file appears.
    _wait_for_ca_cert(juju, app.name)

    if not status.apps.get(app.name).relations.get("oidc"):  # type: ignore
        juju.integrate(f"{app.name}", "hydra")

    juju.wait(
        jubilant.all_active,
        timeout=10 * 60,
        delay=5,
    )

    if not _admin_identity_exists(juju, test_email):
        juju.run(
            "kratos/0",
            "create-admin-account",
            {"email": test_email, "password": test_password, "username": test_username},
        )

    try:
        secret_id = juju.add_secret(test_secret, {"password": test_password})
    except jubilant.CLIError as e:
        if e.stderr != f'ERROR secret with name "{test_secret}" already exists\n':
            raise e
        secrets = json.loads(juju.cli("secrets", "--format", "json"))
        secret_id = [
            secret for secret in secrets if secrets[secret].get("name") == test_secret
        ][0]

    juju.cli("grant-secret", secret_id, "kratos")
    result = juju.run(
        "kratos/0",
        "reset-password",
        {"email": test_email, "password-secret-id": secret_id.split(":")[-1]},
    )
    logger.info("results reset-password %s", result.results)

    res = json.loads(
        juju.run("traefik-public/0", "show-proxied-endpoints").results[
            "proxied-endpoints"
        ]
    )
    logger.info("result show-proxied %s", res)

    # make sure the app is alive (NetBox may still be restarting after OIDC relation setup)
    response = http.get(res[app.name]["url"], timeout=30, verify=False)
    assert response.status_code == 200

    # Capture container logs before attempting the OIDC flow for debugging
    try:
        pebble_logs = juju.cli(
            "ssh",
            "--container",
            "django-app",
            f"{app.name}/0",
            "sh",
            "-c",
            "cat /var/log/django-app/*.log 2>/dev/null || echo 'no logs'",
        )
        logger.info("Container logs before OIDC flow:\n%s", pebble_logs[-2000:])
    except jubilant.CLIError as e:
        logger.info("Could not fetch container logs: %s", e)

    _assert_idp_login_success(res[app.name]["url"], endpoint, test_email, test_password)


def _admin_identity_exists(juju, test_email):
    """Check if the admin identity already exists in Kratos."""
    try:
        res = juju.run("kratos/0", "get-identity", {"email": test_email})
        return res.status == "completed"
    except jubilant.TaskError as e:
        logger.info("Error checking admin identity: %s", e)
        return False


def _wait_for_ca_cert(juju: jubilant.Juju, app_name: str, timeout: int = 300):
    """Ensure the CA certificate bundle is available in the workload container.

    Due to event ordering in the ``certificate_transfer`` relation, the charm
    may not push the CA file on its own in time.  This helper:

    1. Polls ``juju show-unit`` until the CA cert appears in the relation
       databag.
    2. Extracts the PEM certificate from the databag.
    3. Reads the system CA bundle from the container, appends the custom CA,
       and writes the combined bundle directly into the container.
    4. Triggers a ``config-changed`` hook so the charm restarts the
       workload (which picks up ``REQUESTS_CA_BUNDLE``).

    Args:
        juju: The Juju instance.
        app_name: The name of the application.
        timeout: Maximum seconds to wait.
    """
    ca_cert_path = "/app/ca-certificates.crt"
    deadline = time.monotonic() + timeout

    container = "django-app"
    while time.monotonic() < deadline:
        # Check if the file already exists in the container
        try:
            juju.cli(
                "ssh",
                "--container",
                container,
                f"{app_name}/0",
                "test",
                "-s",
                ca_cert_path,
            )
            logger.info("CA cert file found at %s", ca_cert_path)
            return
        except jubilant.CLIError:
            pass

        # Try to extract the cert from the relation databag
        pem_certs = _extract_certs_from_databag(juju, app_name)
        if pem_certs:
            logger.info(
                "Extracted %d CA certs from databag, pushing to container",
                len(pem_certs),
            )
            _push_ca_bundle(juju, app_name, pem_certs, ca_cert_path)
            # Trigger config-changed so the charm restarts gunicorn, which
            # will pick up the REQUESTS_CA_BUNDLE env var.
            _trigger_config_changed(juju, app_name)
            # Wait for the model to settle after the config change
            juju.wait(
                jubilant.all_active,
                timeout=5 * 60,
                delay=5,
            )
            # Verify the file is now present
            try:
                juju.cli(
                    "ssh",
                    "--container",
                    container,
                    f"{app_name}/0",
                    "test",
                    "-s",
                    ca_cert_path,
                )
                logger.info("CA cert file confirmed at %s", ca_cert_path)
                return
            except jubilant.CLIError:
                logger.info("File push succeeded but file not found?")

        logger.info("Waiting for CA cert in databag ...")
        time.sleep(10)

    pytest.fail(f"CA cert not available after {timeout}s")


def _extract_certs_from_databag(
    juju: jubilant.Juju,
    app_name: str,
) -> list:
    """Extract PEM certificates from the receive-ca-cert relation databag.

    Args:
        juju: The Juju instance.
        app_name: The name of the application.

    Returns:
        List of PEM certificate strings, or empty list if not found.
    """
    try:
        show_out = juju.cli(
            "show-unit",
            f"{app_name}/0",
            "--format",
            "json",
        )
        unit_data = json.loads(show_out)
        unit_info = unit_data.get(f"{app_name}/0", {})
        for rel in unit_info.get("relation-info", []):
            if rel.get("endpoint") == "receive-ca-cert":
                app_data = rel.get("application-data", {})
                certs_raw = app_data.get("certificates", "")
                if certs_raw:
                    parsed = json.loads(certs_raw)
                    if isinstance(parsed, list) and parsed:
                        return [c for c in parsed if c.strip()]
    except Exception as exc:  # noqa: BLE001
        logger.info("Error reading relation databag: %s", exc)
    return []


def _push_ca_bundle(
    juju: jubilant.Juju,
    app_name: str,
    pem_certs: list,
    dest_path: str,
) -> None:
    """Push a combined CA bundle into the workload container.

    Reads the existing system CA bundle, appends the custom certs, and
    writes the result to *dest_path* inside the container.

    Args:
        juju: The Juju instance.
        app_name: The name of the application.
        pem_certs: List of PEM certificate strings to append.
        dest_path: Path inside the container to write the bundle.
    """
    container = "django-app"
    # Read the system CA bundle
    system_ca = ""
    try:
        system_ca = juju.cli(
            "ssh",
            "--container",
            container,
            f"{app_name}/0",
            "cat",
            "/etc/ssl/certs/ca-certificates.crt",
        )
    except jubilant.CLIError:
        logger.info("Could not read system CA bundle, using empty base")

    combined = system_ca.rstrip("\n")
    for cert in pem_certs:
        combined += "\n\n" + cert.strip()
    combined += "\n"

    # Write via stdin piped through juju ssh
    juju.cli(
        "ssh",
        "--container",
        container,
        f"{app_name}/0",
        "sh",
        "-c",
        f"cat > {dest_path}",
        stdin=combined,
    )
    logger.info("Pushed combined CA bundle to %s", dest_path)


def _trigger_config_changed(juju: jubilant.Juju, app_name: str) -> None:
    """Trigger a config-changed hook by toggling a config value.

    Juju only fires ``config-changed`` when the value actually differs
    from the current one.  We toggle ``oidc-redirect-path`` to a
    temporary value and immediately reset it so the hook fires at least
    once, causing the charm to restart gunicorn.

    Args:
        juju: The Juju instance.
        app_name: The name of the application.
    """
    temp_value = "/oauth/complete/oidc/tmp"
    default_value = "/oauth/complete/oidc/"
    juju.cli("config", app_name, f"oidc-redirect-path={temp_value}")
    # Give Juju a moment to dispatch the hook before resetting
    time.sleep(10)
    juju.cli("config", app_name, f"oidc-redirect-path={default_value}")


def _assert_idp_login_success(
    app_url: str, endpoint: str, test_email: str, test_password: str
):
    """Use playwright to test the OIDC login flow."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        return_path = urlparse(url=app_url).path
        page.goto(f"{app_url}/oauth/login/oidc/?next={return_path}/")
        expect(page).not_to_have_title(re.compile("Sign in failed"))
        page.get_by_label("Email").fill(test_email)
        page.get_by_label("Password").fill(test_password)
        page.get_by_role("button", name="Sign in").click()
        # Wait longer for the OIDC token exchange (server-side HTTP call)
        try:
            expect(page).to_have_url(f"{app_url}/", timeout=60_000)
        except AssertionError:
            logger.error("OIDC callback did not redirect to home page")
            logger.error("Current URL: %s", page.url)
            logger.error("Page title: %s", page.title())
            logger.error("Page content:\n%s", page.content())
            raise
        cont = page.content()
        assert "<title>Home | NetBox</title>" in cont
        cont = page.content()
        # The user is logged in.
        assert test_email in page.content()
        assert "Log Out" in page.content()
