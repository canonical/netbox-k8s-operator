# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helpers for configuring custom certificate authority trust."""


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
