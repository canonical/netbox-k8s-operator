# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for the NetBox charm tests."""

from pytest import Parser


def pytest_addoption(parser: Parser) -> None:
    """Parse additional pytest options.

    Args:
        parser: Pytest parser.
    """
    parser.addoption("--kube-config", action="store", default="~/.kube/config")
    parser.addoption("--localstack-address", action="store")
