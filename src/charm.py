#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""NetBox charm entrypoint."""

import logging
from collections.abc import Generator

import ops
import paas_charm.django
from charms.redis_k8s.v0.redis import RedisRelationCharmEvents

from relations import CertificatesRelation, RedisRelation

logger = logging.getLogger(__name__)

POSTGRESQL_RELATION_NAME = "postgresql"
MINIMUM_POSTGRESQL_MAJOR_VERSION = 15


class NetboxCharm(paas_charm.django.Charm):
    """NetBox service with custom certificate trust and legacy Redis integration."""

    on = RedisRelationCharmEvents()  # type: ignore[assignment]
    custom_relations = [CertificatesRelation, RedisRelation]

    def _missing_custom_relations(self) -> Generator[str, None, None]:
        """Report Valkey, the default cache, when no cache integration is present.

        Yields:
            Names of the missing required integrations.
        """
        for name in super()._missing_custom_relations():
            yield "valkey" if name == RedisRelation.relation_name else name

    def is_ready(self) -> bool:
        """Check that the charm is ready, including the PostgreSQL version.

        Returns:
            True if the charm is ready to start the workload application.
        """
        if not super().is_ready():
            return False
        version = self._postgresql_version()
        if version is None:
            return True
        try:
            major = int(version.split(".", maxsplit=1)[0])
        except ValueError:
            logger.warning("Could not parse the PostgreSQL version %r", version)
            return True
        if major < MINIMUM_POSTGRESQL_MAJOR_VERSION:
            self.update_app_and_unit_status(
                ops.BlockedStatus(
                    f"NetBox requires PostgreSQL {MINIMUM_POSTGRESQL_MAJOR_VERSION}+, "
                    f"found {version}"
                )
            )
            return False
        return True

    def _postgresql_version(self) -> str | None:
        """Get the PostgreSQL version published in the relation data.

        Returns:
            The version, or None if the relation or the version field is missing.
        """
        relation = self.model.get_relation(POSTGRESQL_RELATION_NAME)
        if relation is None or relation.app is None:
            return None
        version = relation.data[relation.app].get("version")
        if not version:
            logger.warning(
                "The PostgreSQL version is not published, skipping the PostgreSQL %s+ check",
                MINIMUM_POSTGRESQL_MAJOR_VERSION,
            )
            return None
        return version


if __name__ == "__main__":
    ops.main(NetboxCharm)
