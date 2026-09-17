# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for custom certificate authority trust helpers."""

from ca_trust import build_ca_bundle, create_ca_layer


def test_build_ca_bundle() -> None:
    """
    arrange: A system CA bundle and unordered custom certificates are provided.
    act: Build the combined CA bundle.
    assert: The system bundle is retained and custom certificates are normalized.
    """
    bundle = build_ca_bundle("SYSTEM CA\n", {"CUSTOM CA 2\n", "CUSTOM CA 1"})

    assert bundle == "SYSTEM CA\n\nCUSTOM CA 1\n\nCUSTOM CA 2\n"


def test_build_ca_bundle_without_system_bundle() -> None:
    """
    arrange: The system CA bundle is unavailable.
    act: Build a bundle containing a custom certificate.
    assert: The resulting bundle remains valid and has one trailing newline.
    """
    bundle = build_ca_bundle("", {"CUSTOM CA"})

    assert bundle == "CUSTOM CA\n"


def test_create_ca_layer() -> None:
    """
    arrange: A workload service and CA bundle path are provided.
    act: Create the Pebble overlay.
    assert: Both supported TLS clients use the requested bundle.
    """
    layer = create_ca_layer("django", "/app/ca-certificates.crt")

    assert layer.to_dict() == {
        "services": {
            "django": {
                "override": "merge",
                "environment": {
                    "REQUESTS_CA_BUNDLE": "/app/ca-certificates.crt",
                    "SSL_CERT_FILE": "/app/ca-certificates.crt",
                },
            },
        },
    }
