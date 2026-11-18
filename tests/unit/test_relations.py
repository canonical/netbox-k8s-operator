# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Lifecycle tests for NetBox's custom relations."""

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import TypeVar
from unittest.mock import patch

import pytest
import yaml
from ops import testing
from paas_charm.relations import CustomRelation, RelationDataError

from charm import NetboxCharm
from relations import (
    CA_CERT_PATH,
    SYSTEM_CA_CERT_PATH,
    CertificatesRelation,
    RedisRelation,
    redis_environment,
)

T = TypeVar("T", bound=CustomRelation)


@pytest.fixture
def context(tmp_path: Path) -> Iterator[testing.Context[NetboxCharm]]:
    """Run the actual root charm with its extension-provided metadata."""
    manifest = yaml.safe_load(Path("charmcraft.yaml").read_text())
    manifest.update(
        containers={"app": {"resource": "app-image"}},
        resources={"app-image": {"type": "oci-image"}},
        peers={"peers": {"interface": "peers"}},
        provides={
            "metrics-endpoint": {"interface": "prometheus_scrape"},
            "grafana-dashboard": {"interface": "grafana_dashboard"},
        },
    )
    manifest["requires"].update(
        ingress={"interface": "ingress", "limit": 1},
        logging={"interface": "loki_push_api"},
    )
    # The COS directory is built under the charm directory, which does not exist in a unit test.
    with patch.object(NetboxCharm, "build_cos_dir", return_value=tmp_path):
        yield testing.Context(
            NetboxCharm,
            meta=manifest,
            actions={
                "rotate-secret-key": {},
                "create-superuser": {
                    "params": {"username": {"type": "string"}, "email": {"type": "string"}}
                },
            },
        )


def make_state(
    relations: list[testing.Relation] | None = None,
    containers: list[testing.Container] | None = None,
) -> testing.State:
    return testing.State(
        leader=True,
        relations=[testing.PeerRelation("peers"), *(relations or [])],
        containers=containers or [testing.Container("app", can_connect=False)],
    )


def redis_relation(hostname: str = "redis-host", port: str = "6379") -> testing.Relation:
    return testing.Relation(
        "redis",
        interface="redis",
        remote_app_name="redis-k8s",
        remote_units_data={0: {"hostname": hostname, "port": port}},
    )


def valkey_relation() -> testing.Relation:
    return testing.Relation("valkey", interface="valkey_client", remote_app_name="valkey")


def get_relation(charm: NetboxCharm, relation_type: type[T]) -> T:
    return next(
        relation for relation in charm._custom_relations if isinstance(relation, relation_type)
    )


def missing_integrations(charm: NetboxCharm) -> list[str]:
    return list(charm._missing_custom_relations())


def test_root_charm_registers_custom_relations(context: testing.Context[NetboxCharm]) -> None:
    state = make_state()

    with context(context.on.update_status(), state) as manager:
        assert {relation.relation_name for relation in manager.charm._custom_relations} == {
            "certificates",
            "redis",
        }


@pytest.mark.parametrize(
    "endpoint, expected",
    [
        ("redis-host:6379", {"REDIS_DB_HOSTNAME": "redis-host", "REDIS_DB_PORT": "6379"}),
        ("redis://host:6379", {"REDIS_DB_HOSTNAME": "host", "REDIS_DB_PORT": "6379"}),
        ("valkey://host:6379", {"REDIS_DB_HOSTNAME": "host", "REDIS_DB_PORT": "6379"}),
        ("[::1]:6380", {"REDIS_DB_HOSTNAME": "::1", "REDIS_DB_PORT": "6380"}),
    ],
)
def test_redis_endpoint_formats(endpoint: str, expected: dict[str, str]) -> None:
    assert redis_environment(endpoint) == expected


@pytest.mark.parametrize(
    "endpoint",
    [
        "",
        "None",
        "localhost",
        "host:abc",
        "host:0",
        "host:65536",
        "redis://:6379",
        "redis://user@host:6379",
        "rediss://host:6379",
    ],
)
def test_redis_rejects_invalid_endpoints(endpoint: str) -> None:
    assert redis_environment(endpoint) == {}


def test_redis_environment(context: testing.Context[NetboxCharm]) -> None:
    state = make_state(relations=[redis_relation()])

    with context(context.on.update_status(), state) as manager:
        redis = get_relation(manager.charm, RedisRelation)
        redis.ensure_ready()
        assert redis.gen_environment() == {
            "REDIS_DB_HOSTNAME": "redis-host",
            "REDIS_DB_PORT": "6379",
        }
        assert missing_integrations(manager.charm) == []


def test_redis_removal_requires_a_cache(context: testing.Context[NetboxCharm]) -> None:
    relation = redis_relation()
    state = make_state(relations=[relation])

    with context(context.on.relation_broken(relation), state) as manager:
        manager.run()
        assert get_relation(manager.charm, RedisRelation).gen_environment() == {}
        assert missing_integrations(manager.charm) == ["valkey"]


def test_redis_without_port_is_not_ready(context: testing.Context[NetboxCharm]) -> None:
    state = make_state(relations=[redis_relation(port="None")])

    with context(context.on.update_status(), state) as manager:
        assert get_relation(manager.charm, RedisRelation).gen_environment() == {}
        with pytest.raises(RelationDataError):
            missing_integrations(manager.charm)


def test_no_cache_reports_valkey_as_missing(context: testing.Context[NetboxCharm]) -> None:
    state = make_state()

    with context(context.on.update_status(), state) as manager:
        assert get_relation(manager.charm, RedisRelation).required
        assert missing_integrations(manager.charm) == ["valkey"]


def test_valkey_only_is_ready(context: testing.Context[NetboxCharm]) -> None:
    state = make_state(relations=[valkey_relation()])

    with context(context.on.update_status(), state) as manager:
        assert not get_relation(manager.charm, RedisRelation).required
        assert missing_integrations(manager.charm) == []


def test_redis_and_valkey_together_are_rejected(context: testing.Context[NetboxCharm]) -> None:
    state = make_state(relations=[redis_relation(), valkey_relation()])

    with context(context.on.update_status(), state) as manager:
        with pytest.raises(RelationDataError, match="only one of"):
            missing_integrations(manager.charm)


def test_adding_valkey_reconciles_without_credentials(
    context: testing.Context[NetboxCharm],
) -> None:
    valkey = valkey_relation()
    state = make_state(relations=[redis_relation(), valkey])

    with context(context.on.relation_created(valkey), state) as manager:
        # Reconciling also runs the workload startup, which a unit test cannot provide.
        with patch.object(get_relation(manager.charm, RedisRelation), "_on_change") as on_change:
            manager.run()
        on_change.assert_called()
        with pytest.raises(RelationDataError, match="only one of"):
            missing_integrations(manager.charm)


def test_certificates_install_and_remove_ca(
    context: testing.Context[NetboxCharm], tmp_path: Path
) -> None:
    certs_dir = tmp_path / "certs"
    app_dir = tmp_path / "app"
    certs_dir.mkdir()
    app_dir.mkdir()
    (certs_dir / "ca-certificates.crt").write_text("SYSTEM CA\n")
    relation = testing.Relation("certificates", interface="tls-certificates")
    container = testing.Container(
        "app",
        can_connect=True,
        mounts={
            "certs": testing.Mount(location="/etc/ssl/certs", source=certs_dir),
            "app": testing.Mount(location="/app", source=app_dir),
        },
    )
    state = make_state(relations=[relation], containers=[container])

    with context(context.on.update_status(), state) as manager:
        certificates = get_relation(manager.charm, CertificatesRelation)
        # The TLS library requires a certificate provider to assign certificates.
        with patch.object(
            certificates._certificates,
            "get_assigned_certificates",
            return_value=([SimpleNamespace(ca="CUSTOM CA")], None),
        ):
            environment = certificates.gen_environment()

    assert (app_dir / "ca-certificates.crt").read_text() == "SYSTEM CA\n\nCUSTOM CA\n"
    assert environment == {"REQUESTS_CA_BUNDLE": CA_CERT_PATH, "SSL_CERT_FILE": CA_CERT_PATH}

    with context(context.on.relation_broken(relation), state) as manager:
        manager.run()
        environment = get_relation(manager.charm, CertificatesRelation).gen_environment()

    assert not (app_dir / "ca-certificates.crt").exists()
    assert environment == {
        "REQUESTS_CA_BUNDLE": SYSTEM_CA_CERT_PATH,
        "SSL_CERT_FILE": SYSTEM_CA_CERT_PATH,
    }


def test_certificates_wait_for_container(context: testing.Context[NetboxCharm]) -> None:
    state = make_state(
        relations=[testing.Relation("certificates", interface="tls-certificates")],
    )

    with context(context.on.update_status(), state) as manager:
        assert get_relation(manager.charm, CertificatesRelation).gen_environment() == {}
