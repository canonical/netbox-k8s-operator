#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""NetBox charm entrypoint."""

import ops
import paas_charm.django

from relations import CertificatesRelation, RedisRelation, ValkeyRelation


class NetboxCharm(paas_charm.django.Charm):
    """NetBox service with custom certificate trust and cache integrations."""

    custom_relations = [CertificatesRelation, RedisRelation, ValkeyRelation]

    def _init_valkey(self, requires: dict[str, ops.RelationMeta]) -> None:
        """Let the custom relation own Valkey instead of the built-in adapter."""
        # paas-charm 2.0.dev4 otherwise creates a second requirer for this endpoint.
        return None

    def is_ready(self) -> bool:
        """Require exactly one Redis-compatible cache integration.

        Returns:
            Whether the workload's integrations are ready.
        """
        if not super().is_ready():
            return False
        caches = [
            name
            for name in ("redis", "valkey")
            if any(relation.active for relation in self.model.relations[name])
        ]
        if len(caches) != 1:
            message = (
                "Integrate either redis or valkey"
                if not caches
                else "Integrate only one of redis or valkey"
            )
            self._stop_all_and_set_blocked(message)
            return False
        return True


if __name__ == "__main__":
    ops.main(NetboxCharm)
