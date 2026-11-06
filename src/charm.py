#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""NetBox charm entrypoint."""

import ops
import paas_charm.django
from charms.redis_k8s.v0.redis import RedisRelationCharmEvents

from relations import CertificatesRelation, RedisRelation, ValkeyRelation


class NetboxCharm(paas_charm.django.Charm):
    """NetBox service with custom certificate trust and cache integrations."""

    on = RedisRelationCharmEvents()  # type: ignore[assignment]
    custom_relations = [CertificatesRelation, RedisRelation, ValkeyRelation]


if __name__ == "__main__":
    ops.main(NetboxCharm)
