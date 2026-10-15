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

    def _init_valkey(self, requires: dict[str, ops.RelationMeta]) -> None:
        """Let the custom relation own Valkey instead of the built-in adapter."""
        # paas-charm 2.0.dev4 otherwise creates a second requirer for this endpoint.
        return None


if __name__ == "__main__":
    ops.main(NetboxCharm)
