# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tests for NetBox configuration module."""

from __future__ import annotations

import runpy
from pathlib import Path


def test_allowed_hosts_and_csrf_trusted_origins_are_deduplicated(monkeypatch) -> None:
    """Set CSRF trusted origins from allowed hosts and drop duplicates."""
    monkeypatch.setenv("DJANGO_SECRET_KEY", "secret-key")
    monkeypatch.setenv(
        "DJANGO_ALLOWED_HOSTS",
        '["netbox.example.com", "netbox.example.com", "https://other.example.com"]',
    )

    module_globals = runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "configuration.py"),
    )

    assert module_globals["ALLOWED_HOSTS"] == [
        "netbox.example.com",
        "https://other.example.com",
    ]
    assert module_globals["CSRF_TRUSTED_ORIGINS"] == [
        "https://netbox.example.com",
        "https://other.example.com",
    ]
