#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""NetBox charm entrypoint."""

import ops
import paas_charm.django

from relations import CertificatesRelation, ValkeyRelation


class NetboxCharm(paas_charm.django.Charm):
    """NetBox service with custom certificate trust and cache integrations."""

    custom_relations = [CertificatesRelation, ValkeyRelation]


if __name__ == "__main__":
    ops.main(NetboxCharm)
