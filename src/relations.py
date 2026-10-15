# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Custom certificate trust and Redis-compatible cache relations."""

import logging
from urllib.parse import urlsplit

import ops
from charms.tls_certificates_interface.v4.tls_certificates import (
    CertificateRequestAttributes,
    Mode,
    TLSCertificatesRequiresV4,
)
from paas_charm.relations import CustomRelation, OnChange, RelationDataError
from paas_charm.valkey import ValkeyClientRequirer

from ca_trust import build_ca_bundle

logger = logging.getLogger(__name__)

CA_CERT_PATH = "/app/ca-certificates.crt"
SYSTEM_CA_CERT_PATH = "/etc/ssl/certs/ca-certificates.crt"


class CertificatesRelation(CustomRelation):
    """Install related CA certificates before the framework starts the workload."""

    relation_name = "certificates"

    def setup(self, on_change: OnChange) -> None:
        """Request certificates and reconcile when trust changes.

        Args:
            on_change: Framework reconcile callback.
        """
        self._on_change = on_change
        self._broken = False
        self._certificates = TLSCertificatesRequiresV4(
            charm=self.charm,
            relationship_name=self.relation_name,
            certificate_requests=[CertificateRequestAttributes(common_name=self.context.app_name)],
            mode=Mode.UNIT,
        )
        self.framework.observe(
            self._certificates.on.certificate_available, self._on_certificate_available
        )
        self.framework.observe(
            self.charm.on[self.relation_name].relation_broken, self._on_relation_broken
        )

    def _on_certificate_available(self, _event: ops.EventBase) -> None:
        """Reconcile the workload after receiving a certificate."""
        self._on_change()

    def _on_relation_broken(self, _event: ops.RelationBrokenEvent) -> None:
        """Exclude certificates from the departing relation and reconcile."""
        self._broken = True
        self._on_change()

    def gen_environment(self) -> dict[str, str]:
        """Synchronize the CA bundle and return the workload trust environment.

        Returns:
            Environment variables pointing all workload processes at the CA bundle.
        """
        container = self.charm.unit.get_container(self.context.container_name)
        if not container.can_connect():
            logger.info("Workload container is not ready for CA certificate installation")
            return {}

        ca_certificates: set[str] = set()
        if not self._broken:
            assigned, _ = self._certificates.get_assigned_certificates()
            ca_certificates = {
                str(certificate.ca).strip()
                for certificate in assigned
                if certificate.ca and str(certificate.ca).strip()
            }

        path = SYSTEM_CA_CERT_PATH
        if ca_certificates:
            system_bundle = (
                container.pull(SYSTEM_CA_CERT_PATH).read()
                if container.exists(SYSTEM_CA_CERT_PATH)
                else ""
            )
            container.push(
                CA_CERT_PATH, build_ca_bundle(system_bundle, ca_certificates), make_dirs=True
            )
            path = CA_CERT_PATH
        elif container.exists(CA_CERT_PATH):
            container.remove_path(CA_CERT_PATH)

        return {"REQUESTS_CA_BUNDLE": path, "SSL_CERT_FILE": path}


class ValkeyRelation(CustomRelation):
    """Expose Valkey credentials using the Redis variables consumed by NetBox."""

    relation_name = "valkey"

    def setup(self, on_change: OnChange) -> None:
        """Wire the Valkey requirer and refresh the workload after cache changes.

        Args:
            on_change: Framework reconcile callback.
        """
        self._on_change = on_change
        self._broken = False
        self._valkey = ValkeyClientRequirer(self.charm, relation_name=self.relation_name)
        self.framework.observe(
            self._valkey.valkey_interface.on.resource_created, self._on_resource_changed
        )
        self.framework.observe(
            self._valkey.valkey_interface.on.endpoints_changed, self._on_resource_changed
        )
        self.framework.observe(
            self._valkey.valkey_interface.on.authentication_updated, self._on_resource_changed
        )
        self.framework.observe(
            self.charm.on[self.relation_name].relation_broken, self._on_relation_broken
        )

    def _on_resource_changed(self, _event: ops.EventBase) -> None:
        """Restart with the latest endpoint and credentials."""
        self._on_change()

    def _on_relation_broken(self, _event: ops.RelationBrokenEvent) -> None:
        """Discard the departing relation's credentials and reconcile."""
        self._broken = True
        self._on_change()

    def ensure_ready(self) -> None:
        """Validate Valkey connection data, including unsupported TLS.

        Raises:
            RelationDataError: If the Valkey data is absent, invalid, or unsupported.
        """
        if self._broken or not self._valkey.to_relation_data():
            raise RelationDataError("Valkey relation data is not ready", self.relation_name)
        if not self.gen_environment():
            raise RelationDataError("Valkey endpoint is invalid", self.relation_name)

    def gen_environment(self) -> dict[str, str]:
        """Translate the framework's Valkey environment to Redis-compatible names.

        Returns:
            Redis connection variables, or an empty mapping until credentials are ready.
        """
        if self._broken:
            return {}
        try:
            data = self._valkey.to_relation_data()
        except RelationDataError:
            logger.warning("Valkey relation data is not ready", exc_info=True)
            return {}
        if not data or not data.endpoints:
            return {}
        endpoint = str(data.endpoints)
        try:
            parsed = urlsplit(endpoint if "://" in endpoint else f"redis://{endpoint}")
            port = parsed.port
        except ValueError:
            logger.warning("Valkey provider supplied an invalid endpoint")
            return {}
        if (
            not parsed.hostname
            or not port
            or parsed.scheme not in ("redis", "valkey")
            or parsed.username
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            logger.warning("Valkey provider supplied an invalid Redis-compatible endpoint")
            return {}
        return {
            "REDIS_DB_HOSTNAME": parsed.hostname,
            "REDIS_DB_PORT": str(port),
            "REDIS_DB_USERNAME": data.username or "",
            "REDIS_DB_PASSWORD": data.password or "",
        }
