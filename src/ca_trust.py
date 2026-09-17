# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helpers for configuring custom certificate authority trust."""

import ops

REQUESTS_CA_BUNDLE = "REQUESTS_CA_BUNDLE"
SSL_CERT_FILE = "SSL_CERT_FILE"


def build_ca_bundle(system_ca_bundle: str, ca_certificates: set[str]) -> str:
    """Combine the system CA bundle with custom CA certificates.

    Args:
        system_ca_bundle: System CA certificates in PEM format.
        ca_certificates: Custom CA certificates in PEM format.

    Returns:
        Combined CA certificates in PEM format.
    """
    certificates = [system_ca_bundle.rstrip("\n")]
    certificates.extend(certificate.strip() for certificate in sorted(ca_certificates))
    return "\n\n".join(filter(None, certificates)) + "\n"


def create_ca_layer(service_name: str, ca_cert_path: str) -> ops.pebble.Layer:
    """Create a Pebble layer that configures the service CA bundle.

    Args:
        service_name: Name of the Pebble workload service.
        ca_cert_path: Path to the CA certificate bundle.

    Returns:
        Pebble layer configuring the workload TLS environment.
    """
    return ops.pebble.Layer(
        {
            "services": {
                service_name: {
                    "override": "merge",
                    "environment": {
                        REQUESTS_CA_BUNDLE: ca_cert_path,
                        SSL_CERT_FILE: ca_cert_path,
                    },
                },
            },
        }
    )
