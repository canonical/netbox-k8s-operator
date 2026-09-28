# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for the NetBox charm integration tests."""

import logging
import socket
import subprocess
from collections.abc import Generator
from typing import cast

import boto3
import jubilant
import kubernetes
import pytest
import requests
from botocore.client import BaseClient
from botocore.config import Config as BotoConfig
from requests import HTTPError
from requests.adapters import HTTPAdapter
from saml_test_helper import SamlK8sTestHelper
from urllib3.util.retry import Retry

from tests.integration.types import App

logger = logging.getLogger(__name__)

# pylint things `juju`` is redefined, but it's a fixture
# pylint: disable=redefined-outer-name

NETBOX_APP_NAME = "netbox-k8s"
GATEWAY_APP_NAME = "gateway-api-integrator"
POSTGRESQL_APP_NAME = "postgresql-k8s"
REDIS_APP_NAME = "redis-k8s"
SAML_APP_NAME = "saml-integrator"
S3_INTEGRATOR_APP_NAME = "s3-integrator"
MICROCEPH_PORT = 7480


@pytest.fixture(scope="module", name="netbox_hostname")
def netbox_hostname_fixture() -> str:
    """Return the name of the NetBox hostname used for tests."""
    return "netbox-k8s.internal"


@pytest.fixture(scope="module", name="netbox_app_image")
def netbox_app_image_fixture(resource_images: dict) -> str:
    """Get NetBox app image from opcli resource images."""
    return resource_images["django-app-image"]


@pytest.fixture(scope="module", name="netbox_charm")
def netbox_charm_fixture(charm_path: str) -> str:
    """Get charm path from opcli."""
    return charm_path


@pytest.fixture(scope="module", name="saml_helper")
def saml_helper_fixture(
    juju: jubilant.Juju,
) -> SamlK8sTestHelper:
    """Return the SamlK8sTestHelper instance used for tests."""
    model_name = juju.status().model.name
    try:
        saml_helper = SamlK8sTestHelper.deploy_saml_idp(model_name)
    except kubernetes.client.ApiException as e:
        if e.reason == "Conflict" and "already exists" in str(e):
            logger.info("SAML IDP already deployed")
            saml_helper = SamlK8sTestHelper(model_name)
        else:
            raise
    return saml_helper


@pytest.fixture(scope="module", name="saml_app")
def saml_app_fixture(
    juju: jubilant.Juju,
) -> App:
    """Deploy saml."""
    if juju.status().apps.get(SAML_APP_NAME):
        logger.info("%s already deployed", SAML_APP_NAME)
        return App(SAML_APP_NAME)
    juju.deploy(
        SAML_APP_NAME,
        channel="latest/edge",
    )
    return App(SAML_APP_NAME)


@pytest.fixture(scope="module", name="netbox_saml_integration")
def netbox_saml_integration_fixture(
    juju: jubilant.Juju,
    saml_app: App,
    netbox_app: App,
    netbox_hostname: str,
    saml_helper: SamlK8sTestHelper,
):
    """Integrate NetBox and SAML for saml integration."""
    juju.config(
        netbox_app.name,
        {
            "saml-sp-entity-id": f"https://{netbox_hostname}",
            # The saml Name for FriendlyName "uid"
            "saml-username": "urn:oid:0.9.2342.19200300.100.1.1",
        },
    )
    model_name = juju.status().model.name
    saml_helper.prepare_pod(model_name, f"{saml_app.name}-0")
    saml_helper.prepare_pod(model_name, f"{netbox_app.name}-0")

    juju.config(
        saml_app.name,
        {
            "entity_id": f"https://{saml_helper.SAML_HOST}/metadata",
            "metadata_url": f"https://{saml_helper.SAML_HOST}/metadata",
        },
    )
    juju.config(
        netbox_app.name,
        {
            "saml-sp-entity-id": f"https://{netbox_hostname}",
            # The saml Name for FriendlyName "uid"
            "saml-username": "urn:oid:0.9.2342.19200300.100.1.1",
        },
    )
    try:
        juju.integrate(saml_app.name, netbox_app.name)
    except jubilant.CLIError as e:
        if "already exists" in str(e):
            logger.info("Relation already exists")
        else:
            raise
    juju.wait(
        lambda status: jubilant.all_active(status, saml_app.name, netbox_app.name),
        timeout=10 * 60,
    )

    # For the saml_helper, a SAML XML metadata for the service is needed.
    # There are instructions to generate it in:
    # https://python-social-auth.readthedocs.io/en/latest/backends/saml.html#basic-usage.
    # This one is instead a minimalistic one that works for the test.
    metadata_xml = f"""
    <md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" cacheDuration="P10D"
                         entityID="https://{netbox_hostname}">
      <md:SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol"
                          AuthnRequestsSigned="false" WantAssertionsSigned="true">
        <md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                                     Location="https://{netbox_hostname}/oauth/complete/saml/"
                                     index="1"/>
      </md:SPSSODescriptor>
    </md:EntityDescriptor>
    """
    try:
        saml_helper.register_service_provider(name=netbox_hostname, metadata=metadata_xml)
    except HTTPError as e:
        if "already exists" in str(e):
            logger.info("Service provider already registered")
        else:
            raise
    return saml_helper


@pytest.fixture(scope="module", name="s3_netbox_configuration")
def s3_netbox_configuration_fixture(s3_address: str) -> dict:
    """Return the S3 configuration to use.

    Returns:
        The S3 configuration as a dict.
    """
    return {
        "endpoint": f"http://{s3_address}:{MICROCEPH_PORT}",
        "bucket": "netboxbucket",
        "path": "/",
        "region": "us-east-1",
        "s3-uri-style": "path",
    }


@pytest.fixture(scope="module", name="s3_netbox_credentials")
def s3_netbox_credentials_fixture() -> dict:
    """Return the S3 AWS credentials to use.

    Returns:
        The S3 credentials as a dict.
    """
    return {"access-key": "test-access-key", "secret-key": "test-secret-key"}


def _host_ip() -> str:
    """Return the host IP that is reachable from Kubernetes workloads."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]


@pytest.fixture(scope="module", name="s3_address")
def s3_address_fixture(pytestconfig: pytest.Config) -> str:
    """Return the address of the MicroCeph RGW service."""
    return pytestconfig.getoption("--s3-address") or _host_ip()


@pytest.fixture(scope="module", name="s3_client")
def s3_client_fixture(
    s3_netbox_configuration: dict,
    s3_netbox_credentials: dict,
) -> BaseClient:
    """Return an S3 client configured for MicroCeph."""
    return boto3.client(
        "s3",
        endpoint_url=s3_netbox_configuration["endpoint"],
        region_name=s3_netbox_configuration["region"],
        aws_access_key_id=s3_netbox_credentials["access-key"],
        aws_secret_access_key=s3_netbox_credentials["secret-key"],
        config=BotoConfig(s3={"addressing_style": "path"}, proxies={}),
    )


@pytest.fixture(scope="session")
def juju(request: pytest.FixtureRequest) -> Generator[jubilant.Juju, None, None]:
    """Pytest fixture that wraps :meth:`jubilant.with_model`."""

    def show_debug_log(juju: jubilant.Juju):
        """Show the juju debug log after the tests.

        Args:
            juju: The Juju instance to get the log from.
        """
        if request.session.testsfailed:
            log = juju.debug_log(limit=1000)
            print(log, end="")

    use_existing = request.config.getoption("--use-existing", default=False)
    if use_existing:
        juju = jubilant.Juju()
        yield juju
        show_debug_log(juju)
        return

    model = request.config.getoption("--model")
    if model:
        juju = jubilant.Juju(model=model)
        yield juju
        show_debug_log(juju)
        return

    keep_models = cast(bool, request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju:
        juju.wait_timeout = 10 * 60
        yield juju
        show_debug_log(juju)
        return


@pytest.fixture(scope="module", name="gateway_app")
def gateway_app_fixture(
    juju: jubilant.Juju,
) -> App:
    """Deploy gateway-api-integrator."""
    if juju.status().apps.get(GATEWAY_APP_NAME):
        logger.info("%s already deployed", GATEWAY_APP_NAME)
        return App(GATEWAY_APP_NAME)

    juju.deploy(GATEWAY_APP_NAME, base="ubuntu@24.04", channel="latest/edge", trust=True)
    return App(GATEWAY_APP_NAME)


@pytest.fixture(scope="module", name="netbox_ingress_integration")
def netbox_ingress_integration_fixture(
    juju: jubilant.Juju,
    gateway_app: App,
    netbox_app: App,
    netbox_hostname: str,
):
    """Integrate NetBox and gateway-api-integrator for ingress integration."""
    juju.config(
        gateway_app.name,
        {
            "external-hostname": netbox_hostname,
            "path-routes": "/",
            "gateway-class": "cilium",
        },
    )
    try:
        juju.integrate(
            netbox_app.name,
            f"{gateway_app.name}:gateway",
        )
    except jubilant.CLIError as e:
        if "already exists" in str(e):
            logger.info("Relation already exists")
        else:
            raise
    juju.wait(
        jubilant.all_active,
        timeout=15 * 60,
    )
    yield netbox_app
    juju.remove_relation(
        f"{netbox_app.name}:ingress",
        f"{gateway_app.name}:ingress",
    )


@pytest.fixture(scope="module", name="s3_integrator_app")
def s3_integrator_app_fixture(
    juju: jubilant.Juju,
    s3_netbox_configuration: dict,
    s3_netbox_credentials: dict,
) -> App:
    """Deploy and configure s3-integrator for MicroCeph."""
    if juju.status().apps.get(S3_INTEGRATOR_APP_NAME):
        logger.info("%s already deployed", S3_INTEGRATOR_APP_NAME)
        return App(S3_INTEGRATOR_APP_NAME)
    juju.deploy(
        S3_INTEGRATOR_APP_NAME,
        channel="edge",
    )
    juju.wait(
        lambda status: jubilant.all_blocked(status, S3_INTEGRATOR_APP_NAME),
        timeout=120,
    )

    juju.config(
        "s3-integrator",
        s3_netbox_configuration,
    )

    task = juju.run(f"{S3_INTEGRATOR_APP_NAME}/0", "sync-s3-credentials", s3_netbox_credentials)
    assert task.status == "completed"
    return App(S3_INTEGRATOR_APP_NAME)


@pytest.fixture(scope="module", name="postgresql_app")
def postgresql_app_fixture(
    juju: jubilant.Juju,
):
    """Deploy and set up postgresql charm needed for the NetBox charm."""
    if juju.status().apps.get(POSTGRESQL_APP_NAME):
        logger.info("%s already deployed", POSTGRESQL_APP_NAME)
        return App(POSTGRESQL_APP_NAME)

    juju_major = juju.version().major
    if juju_major >= 4:
        channel = "16/edge"
        base = "ubuntu@24.04"
        force = True
    else:
        channel = "14/stable"
        base = "ubuntu@22.04"
        force = False

    juju.deploy(
        POSTGRESQL_APP_NAME,
        channel=channel,
        base=base,
        config={"profile": "testing"},
        trust=True,
        force=force,
    )
    return App(POSTGRESQL_APP_NAME)


@pytest.fixture(scope="module", name="redis_app")
def redis_app_fixture(
    juju: jubilant.Juju,
):
    """Deploy and set up postgresql charm needed for the NetBox charm."""
    if juju.status().apps.get(REDIS_APP_NAME):
        logger.info("%s already deployed", REDIS_APP_NAME)
        return App(REDIS_APP_NAME)

    juju.deploy(
        REDIS_APP_NAME,
        channel="edge",
    )
    return App(REDIS_APP_NAME)


@pytest.fixture(scope="module", name="netbox_barebones")
def netbox_barebones_fixture(
    juju: jubilant.Juju,
    netbox_charm: str,
    netbox_app_image: str,
) -> App:
    """Deploy NetBox app without any relations."""
    status = juju.status()
    if NETBOX_APP_NAME in status.apps:
        return App(NETBOX_APP_NAME)

    resources = {
        "django-app-image": netbox_app_image,
    }
    juju.deploy(
        netbox_charm,
        resources=resources,
        config={
            "django-debug": False,
            "django-allowed-hosts": "*",
        },
    )
    return App(NETBOX_APP_NAME)


@pytest.fixture(scope="module", name="netbox_app")
def netbox_app_fixture(
    juju: jubilant.Juju,
    netbox_barebones: App,
    redis_app: App,
    postgresql_app: App,
    s3_integrator_app: App,
) -> App:
    """Deploy NetBox app with necessary integrations."""
    try:
        juju.integrate(
            f"{netbox_barebones.name}:s3",
            f"{s3_integrator_app.name}",
        )
        juju.integrate(
            f"{netbox_barebones.name}:postgresql",
            f"{postgresql_app.name}",
        )
        juju.integrate(
            f"{netbox_barebones.name}:redis",
            f"{redis_app.name}",
        )
    except jubilant.CLIError as e:
        if "already exists" in str(e):
            logger.info("Relation already exists")
        else:
            raise
    juju.wait(
        lambda status: jubilant.all_active(
            status,
            s3_integrator_app.name,
            postgresql_app.name,
            redis_app.name,
            netbox_barebones.name,
        ),
        timeout=15 * 60,
    )

    return App(netbox_barebones.name)


@pytest.fixture(scope="module", name="identity_bundle")
def deploy_identity_bundle_fixture(
    juju: jubilant.Juju,
    postgresql_app: App,
):
    """Deploy Canonical identity bundle."""
    if juju.status().apps.get("hydra"):
        logger.info("identity-platform is already deployed")
        return
    juju.deploy("hydra", channel="latest/edge", revision=399, trust=True)
    juju.deploy("kratos", channel="latest/edge", revision=567, trust=True)
    juju.deploy(
        "identity-platform-login-ui-operator",
        channel="latest/edge",
        revision=200,
        trust=True,
    )
    juju.deploy("self-signed-certificates", channel="1/stable", revision=317, trust=True)
    juju.deploy(
        "traefik-k8s",
        "traefik-admin",
        channel="latest/stable",
        revision=176,
        trust=True,
    )
    juju.deploy("traefik-k8s", "traefik-public", channel="latest/edge", revision=270, trust=True)
    # Integrations
    juju.integrate(
        "hydra:hydra-endpoint-info",
        "identity-platform-login-ui-operator:hydra-endpoint-info",
    )
    juju.integrate("hydra:hydra-endpoint-info", "kratos:hydra-endpoint-info")
    juju.integrate("kratos:kratos-info", "identity-platform-login-ui-operator:kratos-info")
    juju.integrate(
        "hydra:ui-endpoint-info", "identity-platform-login-ui-operator:ui-endpoint-info"
    )
    juju.integrate(
        "kratos:ui-endpoint-info",
        "identity-platform-login-ui-operator:ui-endpoint-info",
    )
    juju.integrate(f"{postgresql_app.name}:database", "hydra:pg-database")
    juju.integrate(f"{postgresql_app.name}:database", "kratos:pg-database")
    juju.integrate("self-signed-certificates:certificates", "traefik-admin:certificates")
    juju.integrate("self-signed-certificates:certificates", "traefik-public:certificates")
    juju.integrate("traefik-public:traefik-route", "hydra:public-route")
    juju.integrate("traefik-public:traefik-route", "kratos:public-route")
    juju.integrate(
        "traefik-public:traefik-route",
        "identity-platform-login-ui-operator:public-route",
    )

    juju.config("kratos", {"enforce_mfa": False})
    yield

    _cleanup(juju)


def _cleanup(juju: jubilant.Juju):
    """Remove the test artifacts created during the test."""
    status = juju.status()

    for app in status.apps:
        juju.remove_application(app, force=True, destroy_storage=True)


@pytest.fixture(scope="session")
def browser_context_manager() -> None:
    """
    A session-scoped fixture that installs the Playwright browser.
    This ensures the browser is installed only for oauth test.
    """
    try:
        subprocess.run(
            ["python", "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Failed to install Playwright browser: {e.stderr}")
    try:
        subprocess.run(
            ["python", "-m", "playwright", "install-deps"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        logger.warning("Could not install Playwright system deps (may require sudo)")


@pytest.fixture(scope="function", name="http")
def fixture_http_client() -> Generator[requests.Session]:
    """Return the --test-flask-image test parameter."""
    retry_strategy = Retry(
        total=5,
        connect=5,
        read=5,
        other=5,
        backoff_factor=5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "POST", "GET", "OPTIONS"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    with requests.Session() as http:
        http.mount("http://", adapter)
        http.mount("https://", adapter)
        yield http
