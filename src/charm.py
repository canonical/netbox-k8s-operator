#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Netbox Charm entrypoint."""

import logging
import typing

import ops
import paas_charm.django

# pylint: disable-next=import-error,no-name-in-module
from charms.tls_certificates_interface.v4.tls_certificates import (
    CertificateAvailableEvent,
    CertificateRequestAttributes,
    Mode,
    TLSCertificatesRequiresV4,
)

# Pebble service name used by the django-framework extension.
_PEBBLE_SERVICE_NAME = "django"

logger = logging.getLogger(__name__)

CA_CERT_PATH = "/app/ca-certificates.crt"
CERTIFICATES_RELATION_NAME = "certificates"


class NetboxCharm(paas_charm.django.Charm):
    """Netbox Charm service."""

    def __init__(self, *args: typing.Any) -> None:
        """Initialize the instance.

        Args:
            args: passthrough to CharmBase.
        """
        super().__init__(*args)
        self._certs = TLSCertificatesRequiresV4(
            charm=self,
            relationship_name=CERTIFICATES_RELATION_NAME,
            certificate_requests=[
                CertificateRequestAttributes(
                    common_name=self.app.name,
                ),
            ],
            mode=Mode.UNIT,
        )
        self.framework.observe(
            self._certs.on.certificate_available,
            self._on_certificate_available,
        )

    def _on_certificate_available(self, _event: CertificateAvailableEvent) -> None:
        """Handle certificate available event.

        Extracts the CA certificate from the event and restarts the service
        so it can use the updated CA bundle for HTTPS connections.
        """
        logger.info("Certificate available via tls-certificates relation")
        self.restart()

    def restart(self, rerun_migrations: bool = False) -> None:
        """Restart the service, pushing CA certificates to the container first.

        Args:
            rerun_migrations: whether it is necessary to run the migrations again.
        """
        self._push_ca_certificates()
        super().restart(rerun_migrations=rerun_migrations)

    def _push_ca_certificates(self) -> None:
        """Push CA certificates to the workload container.

        Reads CA certificates from the tls-certificates relation,
        combines them with the system CA bundle, and writes the result
        to the container so that ``REQUESTS_CA_BUNDLE`` can point to it.
        """
        container = self.unit.get_container(
            self._workload_config.container_name,
        )
        if not container.can_connect():
            logger.info("Container not connectable, skipping CA push")
            return

        ca_certs = self._collect_ca_certificates()
        if not ca_certs:
            logger.info("No CA certificates found in relation data")
            return

        # Read the system CA bundle from the container
        system_ca_bundle = ""
        system_ca_path = "/etc/ssl/certs/ca-certificates.crt"
        if container.exists(system_ca_path):
            system_ca_bundle = container.pull(system_ca_path).read()

        # Combine system CAs with relation CAs
        combined = system_ca_bundle.rstrip("\n")
        for cert in sorted(ca_certs):
            combined += "\n\n" + cert.strip()
        combined += "\n"

        container.push(CA_CERT_PATH, combined, make_dirs=True)
        logger.info(
            "Pushed combined CA bundle to %s (%d custom CAs)",
            CA_CERT_PATH,
            len(ca_certs),
        )

        # Add a Pebble overlay layer that injects REQUESTS_CA_BUNDLE and
        # SSL_CERT_FILE into the service environment.  These must be set
        # in the Pebble layer (not just in configuration.py) because the
        # CA cert file may not exist when Django first starts and the env
        # vars set at Python import time would be too late.
        ca_env_layer = ops.pebble.Layer(
            {
                "services": {
                    _PEBBLE_SERVICE_NAME: {
                        "override": "merge",
                        "environment": {
                            "REQUESTS_CA_BUNDLE": CA_CERT_PATH,
                            "SSL_CERT_FILE": CA_CERT_PATH,
                        },
                    },
                },
            }
        )
        container.add_layer("ca-certs", ca_env_layer, combine=True)
        logger.info(
            "Added Pebble layer with REQUESTS_CA_BUNDLE=%s",
            CA_CERT_PATH,
        )

    def _collect_ca_certificates(self) -> set:
        """Collect CA certificates from the tls-certificates relation.

        Retrieves assigned certificates from the TLSCertificatesRequiresV4
        integration and extracts the CA certificate from each one.

        Returns:
            Set of CA certificate PEM strings.
        """
        ca_certs: set = set()
        try:
            assigned_certs, _ = self._certs.get_assigned_certificates()
            for cert in assigned_certs:
                if cert and cert.ca:
                    ca_pem = str(cert.ca)
                    if ca_pem.strip():
                        ca_certs.add(ca_pem)
                        logger.info("Extracted CA certificate from relation")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(
                "Error retrieving certificates from relation: %s",
                e,
            )

        if ca_certs:
            logger.info(
                "Got %d CA certs from tls-certificates relation",
                len(ca_certs),
            )
        return ca_certs


if __name__ == "__main__":
    ops.main(NetboxCharm)
