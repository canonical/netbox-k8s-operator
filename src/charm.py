#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""NetBox charm entrypoint."""

import typing

import ops
import paas_charm.django
from charms.redis_k8s.v0.redis import RedisRelationCharmEvents
from paas_charm.relations import RelationDataError

from relations import CertificatesRelation, RedisRelation, ValkeyRelation

CACHE_RELATIONS = (RedisRelation.relation_name, ValkeyRelation.relation_name)


class NetboxCharm(paas_charm.django.Charm):
    """NetBox service with custom certificate trust and cache integrations."""

    on = RedisRelationCharmEvents()  # type: ignore[assignment]
    custom_relations = [CertificatesRelation, RedisRelation, ValkeyRelation]

    def _missing_custom_relations(self) -> typing.Generator:
        """Require exactly one cache integration, in addition to the framework checks.

        Yields:
            Names of the missing integrations.

        Raises:
            RelationDataError: If both the Redis and Valkey integrations are present.
        """
        related = [
            name
            for name in CACHE_RELATIONS
            if any(relation.active for relation in self.model.relations.get(name, []))
        ]
        if len(related) > 1:
            raise RelationDataError(
                f"only one of the {' and '.join(CACHE_RELATIONS)} integrations is supported",
                CACHE_RELATIONS[0],
            )
        yield from super()._missing_custom_relations()
        if not related:
            yield " or ".join(CACHE_RELATIONS)


if __name__ == "__main__":
    ops.main(NetboxCharm)
