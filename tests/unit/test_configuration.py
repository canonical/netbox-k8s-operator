# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the NetBox Django configuration module."""

import importlib.util
import json
import os
import pathlib
import sys

import pytest

CONFIG_PATH = pathlib.Path(os.path.dirname(__file__)).parent.parent / "configuration.py"


def _load_configuration(env: dict[str, str]) -> dict:
    """Load configuration.py as a module with the given environment variables.

    Args:
        env: additional environment variables to set.

    Returns:
        The module's namespace as a dictionary.
    """
    module_name = f"_test_config_{abs(hash(frozenset(env.items())))}"
    for key, value in env.items():
        os.environ[key] = value
    os.environ["DJANGO_SECRET_KEY"] = "test-secret-key-12345"
    spec = importlib.util.spec_from_file_location(module_name, CONFIG_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return vars(module)


class TestCsrfTrustedOrigins:
    """Tests for the CSRF_TRUSTED_ORIGINS setting."""

    def test_empty_allowed_hosts(self):
        """
        arrange: No DJANGO_ALLOWED_HOSTS env var is set.
        act: Load the configuration module.
        assert: CSRF_TRUSTED_ORIGINS should be an empty list.
        """
        config = _load_configuration({})
        assert config["CSRF_TRUSTED_ORIGINS"] == []

    def test_matches_allowed_hosts(self):
        """
        arrange: DJANGO_ALLOWED_HOSTS is set to ["example.com", "netbox.local"].
        act: Load the configuration module.
        assert: CSRF_TRUSTED_ORIGINS should contain the same values as ALLOWED_HOSTS.
        """
        hosts = ["example.com", "netbox.local"]
        config = _load_configuration({"DJANGO_ALLOWED_HOSTS": json.dumps(hosts)})
        assert config["CSRF_TRUSTED_ORIGINS"] == hosts

    def test_independent_copy(self):
        """
        arrange: DJANGO_ALLOWED_HOSTS is set to ["example.com"].
        act: Load the configuration module.
        assert: CSRF_TRUSTED_ORIGINS should be an independent copy.
        """
        config = _load_configuration({"DJANGO_ALLOWED_HOSTS": '["example.com"]'})
        assert config["CSRF_TRUSTED_ORIGINS"] is not config["ALLOWED_HOSTS"]

    def test_with_single_host(self):
        """
        arrange: DJANGO_ALLOWED_HOSTS is set to ["netbox.example.com"].
        act: Load the configuration module.
        assert: CSRF_TRUSTED_ORIGINS should contain exactly that host.
        """
        config = _load_configuration({"DJANGO_ALLOWED_HOSTS": '["netbox.example.com"]'})
        assert config["CSRF_TRUSTED_ORIGINS"] == ["netbox.example.com"]

    def test_with_multiple_hosts(self):
        """
        arrange: DJANGO_ALLOWED_HOSTS is set to multiple hosts.
        act: Load the configuration module.
        assert: CSRF_TRUSTED_ORIGINS should contain all of them.
        """
        config = _load_configuration(
            {"DJANGO_ALLOWED_HOSTS": '["host1.example.com", "host2.example.com", "host3.example.com"]'}
        )
        assert config["CSRF_TRUSTED_ORIGINS"] == [
            "host1.example.com",
            "host2.example.com",
            "host3.example.com",
        ]
