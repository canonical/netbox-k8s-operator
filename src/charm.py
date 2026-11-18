#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""NetBox charm entrypoint."""

from collections.abc import Generator

import ops
import paas_charm.django
from charms.redis_k8s.v0.redis import RedisRelationCharmEvents

from relations import CertificatesRelation, RedisRelation


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


if __name__ == "__main__":
    ops.main(NetboxCharm)
