# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Custom certificate trust and legacy Redis relations."""

import logging
from urllib.parse import urlsplit

import ops
from charms.redis_k8s.v0.redis import RedisRequires
from charms.tls_certificates_interface.v4.tls_certificates import (
    CertificateRequestAttributes,
    Mode,
    TLSCertificatesRequiresV4,
)
from paas_charm.relations import CustomRelation, OnChange, RelationDataError

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


def redis_environment(endpoint: str) -> dict[str, str]:
    """Translate a Redis-compatible endpoint to the variables consumed by NetBox.

    Args:
        endpoint: Endpoint as ``host:port`` or ``redis://host:port``.

    Returns:
        Redis connection variables, or an empty mapping if the endpoint is invalid.
    """
    try:
        parsed = urlsplit(endpoint if "://" in endpoint else f"redis://{endpoint}")
        port = parsed.port
    except ValueError:
        logger.warning("Provider supplied an invalid endpoint")
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
        logger.warning("Provider supplied an invalid Redis-compatible endpoint")
        return {}
    return {"REDIS_DB_HOSTNAME": parsed.hostname, "REDIS_DB_PORT": str(port)}


class RedisRelation(CustomRelation):
    """Expose the legacy Redis relation using the variables consumed by NetBox."""

    relation_name = "redis"

    @property
    def required(self) -> bool:
        """Required unless the Valkey integration provides the cache."""
        return not any(
            relation.active for relation in self.charm.model.relations.get("valkey", [])
        )

    def setup(self, on_change: OnChange) -> None:
        """Wire the Redis requirer and refresh the workload after cache changes.

        Args:
            on_change: Framework reconcile callback.
        """
        self._on_change = on_change
        self._broken = False
        self._redis = RedisRequires(self.charm, relation_name=self.relation_name)
        self.framework.observe(self.charm.on.redis_relation_updated, self._on_relation_updated)
        self.framework.observe(
            self.charm.on[self.relation_name].relation_broken, self._on_relation_broken
        )
        # Adding or removing the Valkey integration changes whether the cache is valid.
        self.framework.observe(self.charm.on["valkey"].relation_created, self._on_relation_updated)
        self.framework.observe(self.charm.on["valkey"].relation_broken, self._on_relation_updated)

    def _on_relation_updated(self, _event: ops.EventBase) -> None:
        """Restart with the latest endpoint."""
        self._on_change()

    def _on_relation_broken(self, _event: ops.RelationBrokenEvent) -> None:
        """Discard the departing relation's endpoint and reconcile."""
        self._broken = True
        self._on_change()

    def ensure_ready(self) -> None:
        """Validate Redis connection data.

        Raises:
            RelationDataError: If the Redis data is absent or invalid, or Valkey is also related.
        """
        if any(relation.active for relation in self.charm.model.relations.get("valkey", [])):
            raise RelationDataError(
                "only one of the redis and valkey integrations is supported", self.relation_name
            )
        if self._broken or not self.gen_environment():
            raise RelationDataError("Redis relation data is not ready", self.relation_name)

    def gen_environment(self) -> dict[str, str]:
        """Translate the Redis endpoint to the variables consumed by NetBox.

        Returns:
            Redis connection variables, or an empty mapping until the endpoint is ready.
        """
        if self._broken:
            return {}
        url = self._redis.url
        # The Redis library temporarily publishes a None port while the relation is created.
        if not url or url.endswith(":None"):
            return {}
        return redis_environment(url)
