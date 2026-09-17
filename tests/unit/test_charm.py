# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the NetBox charm."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import ops

from charm import CA_CERT_PATH, SYSTEM_CA_CERT_PATH, NetboxCharm

# pylint: disable=protected-access


def test_push_ca_certificates() -> None:
    """
    arrange: The workload container is connectable and a custom CA is assigned.
    act: Reconcile the CA certificates.
    assert: The combined bundle is pushed and configured for the workload service.
    """
    container = MagicMock(spec=ops.Container)
    container.can_connect.return_value = True
    container.exists.return_value = True
    container.pull.return_value.read.return_value = "SYSTEM CA\n"
    charm: Any = SimpleNamespace(
        unit=MagicMock(),
        _workload_config=SimpleNamespace(container_name="django-app"),
        _collect_ca_certificates=MagicMock(return_value={"CUSTOM CA"}),
        _set_ca_environment=MagicMock(),
    )
    charm.unit.get_container.return_value = container

    NetboxCharm._push_ca_certificates(charm)

    container.pull.assert_called_once_with(SYSTEM_CA_CERT_PATH)
    container.push.assert_called_once_with(
        CA_CERT_PATH,
        "SYSTEM CA\n\nCUSTOM CA\n",
        make_dirs=True,
    )
    charm._set_ca_environment.assert_called_once_with(container, CA_CERT_PATH)


def test_push_ca_certificates_removes_stale_bundle() -> None:
    """
    arrange: No custom CA is assigned.
    act: Reconcile the CA certificates.
    assert: Any stale custom CA configuration is removed.
    """
    container = MagicMock(spec=ops.Container)
    container.can_connect.return_value = True
    charm: Any = SimpleNamespace(
        unit=MagicMock(),
        _workload_config=SimpleNamespace(container_name="django-app"),
        _collect_ca_certificates=MagicMock(return_value=set()),
        _remove_ca_certificates=MagicMock(),
    )
    charm.unit.get_container.return_value = container

    NetboxCharm._push_ca_certificates(charm)

    charm._remove_ca_certificates.assert_called_once_with(container)


def test_remove_ca_certificates_restores_system_trust() -> None:
    """
    arrange: A custom CA bundle exists in the workload container.
    act: Remove the custom CA certificates.
    assert: The bundle is deleted and the system trust store is configured.
    """
    container = MagicMock(spec=ops.Container)
    container.exists.return_value = True
    charm: Any = SimpleNamespace(_set_ca_environment=MagicMock())

    NetboxCharm._remove_ca_certificates(charm, container)

    container.remove_path.assert_called_once_with(CA_CERT_PATH)
    charm._set_ca_environment.assert_called_once_with(container, SYSTEM_CA_CERT_PATH)


def test_certificates_relation_broken_restarts_workload() -> None:
    """
    arrange: The certificates relation is removed.
    act: Handle the relation-broken event.
    assert: The workload is restarted to reconcile its CA trust.
    """
    charm: Any = SimpleNamespace(restart=MagicMock())

    NetboxCharm._on_certificates_relation_broken(charm, MagicMock())

    charm.restart.assert_called_once_with()
