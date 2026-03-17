#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Netbox Charm entrypoint."""

import json
import logging
import typing

import ops
import paas_charm.django
from charms.certificate_transfer_interface.v1.certificate_transfer import (
    CertificateTransferRequires,
)

# Pebble service name used by the django-framework extension.
_PEBBLE_SERVICE_NAME = "django"

logger = logging.getLogger(__name__)

CA_CERT_PATH = "/app/ca-certificates.crt"
RECEIVE_CA_CERT_RELATION_NAME = "receive-ca-cert"


class NetboxCharm(paas_charm.django.Charm):
    """Netbox Charm service."""

    def __init__(self, *args: typing.Any) -> None:
        """Initialize the instance.

        Args:
            args: passthrough to CharmBase.
        """
        super().__init__(*args)
        self._ca_transfer = CertificateTransferRequires(
            charm=self,
            relationship_name=RECEIVE_CA_CERT_RELATION_NAME,
        )
        self.framework.observe(
            self._ca_transfer.on.certificate_set_updated,
            self._on_certificates_updated,
        )
        self.framework.observe(
            self._ca_transfer.on.certificates_removed,
            self._on_certificates_removed,
        )

    def _on_certificates_updated(self, event: ops.EventBase) -> None:
        """Handle CA certificates updated event."""
        logger.info("CA certificates updated via certificate_transfer")
        self.restart()

    def _on_certificates_removed(self, event: ops.EventBase) -> None:
        """Handle CA certificates removed event."""
        logger.info("CA certificates removed via certificate_transfer")
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

        Reads CA certificates from the receive-ca-cert relation databag,
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
        """Collect CA certificates from the receive-ca-cert relation.

        Tries the certificate_transfer library first, then falls back
        to parsing the raw relation databag directly.

        Returns:
            Set of CA certificate PEM strings.
        """
        # Try the library first
        ca_certs = self._ca_transfer.get_all_certificates()
        if ca_certs:
            logger.info(
                "Got %d CA certs from certificate_transfer library",
                len(ca_certs),
            )
            return ca_certs

        # Fallback: parse the raw relation databag directly.
        # This handles cases where the library's data model validation
        # is too strict or the provider uses an unexpected format.
        ca_certs = self._parse_raw_databag()
        if ca_certs:
            logger.info(
                "Got %d CA certs from raw databag fallback",
                len(ca_certs),
            )
        return ca_certs

    def _parse_raw_databag(self) -> set:
        """Parse CA certs directly from the relation databag.

        Handles both v0 (unit databag) and v1 (app databag) formats
        of the ``certificate_transfer`` interface.

        Returns:
            Set of CA certificate PEM strings.
        """
        certs: set = set()
        for rel in self.model.relations.get(RECEIVE_CA_CERT_RELATION_NAME, []):
            if not rel.active:
                continue
            # v1 format: app databag with "certificates" key
            if rel.app:
                app_bag = dict(rel.data.get(rel.app, {}))
                raw = app_bag.get("certificates", "")
                if raw:
                    certs.update(self._parse_cert_value(raw))
            # v0 format: unit databag with "ca" / "chain" keys
            for unit in list(rel.units):
                unit_bag = dict(rel.data.get(unit, {}))
                ca_val = unit_bag.get("ca", "")
                if ca_val:
                    certs.update(self._parse_cert_value(ca_val))
                chain_val = unit_bag.get("chain", "")
                if chain_val:
                    certs.update(self._parse_cert_value(chain_val))
        return certs

    @staticmethod
    def _parse_cert_value(raw: str) -> set:
        """Parse a certificate value that may be JSON-encoded.

        Args:
            raw: A raw string from the relation databag.

        Returns:
            Set of PEM certificate strings.
        """
        certs: set = set()
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                certs.update(c for c in parsed if c.strip())
            elif isinstance(parsed, str) and parsed.strip():
                certs.add(parsed.strip())
        except (json.JSONDecodeError, TypeError):
            if raw.strip():
                certs.add(raw.strip())
        return certs


if __name__ == "__main__":
    ops.main(NetboxCharm)
