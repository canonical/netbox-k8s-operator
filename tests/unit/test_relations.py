# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Lifecycle tests for NetBox's custom relations."""

import json
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import paas_charm.django
import pytest
import yaml
from ops.testing import Harness
from paas_charm.relations import RelationDataError
from paas_charm.valkey import ValkeyTLSNotSupportedError

from charm import NetboxCharm
from relations import (
    CA_CERT_PATH,
    SYSTEM_CA_CERT_PATH,
    CertificatesRelation,
    RedisRelation,
    ValkeyRelation,
)


@pytest.fixture
def harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Harness[NetboxCharm]]:
    """Instantiate the actual root charm with its extension-provided metadata."""
    monkeypatch.setenv("JUJU_VERSION", "3.6.0")
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
    with patch.object(NetboxCharm, "build_cos_dir", return_value=tmp_path):
        instance = Harness(
            NetboxCharm,
            meta=yaml.safe_dump(manifest),
            config=yaml.safe_dump(manifest["config"]),
            actions=yaml.safe_dump(
                {
                    "rotate-secret-key": {},
                    "create-superuser": {
                        "params": {"username": {"type": "string"}, "email": {"type": "string"}}
                    },
                }
            ),
        )
        try:
            instance.begin()
            instance.set_leader(True)
            yield instance
        finally:
            instance.cleanup()


def get_valkey(harness: Harness[NetboxCharm]) -> ValkeyRelation:
    return next(
        relation
        for relation in harness.charm._custom_relations
        if isinstance(relation, ValkeyRelation)
    )


def get_redis(harness: Harness[NetboxCharm]) -> RedisRelation:
    return next(
        relation
        for relation in harness.charm._custom_relations
        if isinstance(relation, RedisRelation)
    )


def get_certificates(harness: Harness[NetboxCharm]) -> CertificatesRelation:
    return next(
        relation
        for relation in harness.charm._custom_relations
        if isinstance(relation, CertificatesRelation)
    )


def provide_valkey(
    harness: Harness[NetboxCharm], relation_id: int, fields: dict[str, str | bool]
) -> None:
    request = json.loads(
        harness.get_relation_data(relation_id, harness.model.app.name)["requests"]
    )[0]
    previous = harness.get_relation_data(relation_id, "valkey-k8s").get("requests")
    response = json.loads(previous)[0] if previous else request.copy()
    response.update(fields)
    harness.update_relation_data(
        relation_id,
        "valkey-k8s",
        {
            "version": "v1",
            "requests": json.dumps([response]),
            "data": json.dumps({request["request-id"]: request}),
        },
    )


def test_root_charm_registers_custom_relations(harness: Harness[NetboxCharm]) -> None:
    assert {relation.relation_name for relation in harness.charm._custom_relations} == {
        "certificates",
        "redis",
        "valkey",
    }
    assert harness.charm._valkey is None


def test_redis_legacy_endpoint_and_removal(harness: Harness[NetboxCharm]) -> None:
    relation_id = harness.add_relation("redis", "redis-k8s")
    harness.add_relation_unit(relation_id, "redis-k8s/0")
    harness.update_relation_data(relation_id, "redis-k8s", {"leader-host": "redis-primary"})
    redis = get_redis(harness)
    with pytest.raises(RelationDataError):
        redis.ensure_ready()
    harness.update_relation_data(
        relation_id, "redis-k8s/0", {"hostname": "redis-unit", "port": "6379"}
    )
    redis.ensure_ready()
    assert redis.gen_environment() == {
        "REDIS_DB_HOSTNAME": "redis-primary",
        "REDIS_DB_PORT": "6379",
        "REDIS_DB_USERNAME": "",
        "REDIS_DB_PASSWORD": "",
    }
    harness.remove_relation(relation_id)
    assert redis.gen_environment() == {}


@pytest.mark.parametrize("port", ["", "None", "abc", "0", "65536"])
def test_redis_waits_for_valid_port(harness: Harness[NetboxCharm], port: str) -> None:
    relation_id = harness.add_relation("redis", "redis-k8s")
    harness.add_relation_unit(relation_id, "redis-k8s/0")
    harness.update_relation_data(relation_id, "redis-k8s/0", {"hostname": "redis", "port": port})
    assert get_redis(harness).gen_environment() == {}
    with pytest.raises(RelationDataError):
        get_redis(harness).ensure_ready()


def test_valkey_reads_secrets_and_removal(harness: Harness[NetboxCharm]) -> None:
    harness.set_leader(True)
    relation_id = harness.add_relation("valkey", "valkey-k8s")
    secret_id = harness.add_model_secret(
        "valkey-k8s", {"username": "netbox", "password": "special:@/?#%"}
    )
    harness.grant_secret(secret_id, "netbox-k8s")
    provide_valkey(
        harness,
        relation_id,
        {"endpoints": "valkey-primary:6379", "secret-user": secret_id},
    )
    valkey = get_valkey(harness)
    valkey.ensure_ready()
    assert valkey.gen_environment() == {
        "REDIS_DB_HOSTNAME": "valkey-primary",
        "REDIS_DB_PORT": "6379",
        "REDIS_DB_USERNAME": "netbox",
        "REDIS_DB_PASSWORD": "special:@/?#%",
    }
    with patch.object(valkey, "_on_change") as on_change:
        harness.set_secret_content(secret_id, {"username": "netbox", "password": "rotated"})
        on_change.assert_called()
    assert valkey.gen_environment()["REDIS_DB_PASSWORD"] == "rotated"
    with patch.object(valkey, "_on_change") as on_change:
        provide_valkey(harness, relation_id, {"endpoints": "valkey-new-primary:6380"})
        on_change.assert_called()
    assert valkey.gen_environment()["REDIS_DB_HOSTNAME"] == "valkey-new-primary"
    harness.remove_relation(relation_id)
    assert valkey.gen_environment() == {}


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
        "rediss://host:6379",
    ],
)
def test_valkey_rejects_invalid_endpoints(harness: Harness[NetboxCharm], endpoint: str) -> None:
    relation_id = harness.add_relation("valkey", "valkey-k8s")
    provide_valkey(
        harness, relation_id, {"endpoints": endpoint, "username": "user", "password": "pw"}
    )
    assert get_valkey(harness).gen_environment() == {}
    with pytest.raises(RelationDataError):
        get_valkey(harness).ensure_ready()


@pytest.mark.parametrize("endpoint", ["valkey://host:6379", "redis://host:6379", "[::1]:6380"])
def test_valkey_endpoint_formats(harness: Harness[NetboxCharm], endpoint: str) -> None:
    relation_id = harness.add_relation("valkey", "valkey-k8s")
    provide_valkey(
        harness, relation_id, {"endpoints": endpoint, "username": "user", "password": "pw"}
    )
    get_valkey(harness).ensure_ready()
    environment = get_valkey(harness).gen_environment()
    assert environment["REDIS_DB_HOSTNAME"] == ("::1" if endpoint.startswith("[") else "host")


def test_valkey_tls_is_blocked(harness: Harness[NetboxCharm]) -> None:
    relation_id = harness.add_relation("valkey", "valkey-k8s")
    provide_valkey(
        harness,
        relation_id,
        {"endpoints": "host:6379", "username": "user", "password": "pw", "tls": True},
    )
    with pytest.raises(ValkeyTLSNotSupportedError):
        get_valkey(harness).ensure_ready()
    assert get_valkey(harness).gen_environment() == {}


def test_valkey_waits_for_provider(harness: Harness[NetboxCharm]) -> None:
    valkey = get_valkey(harness)
    assert valkey.gen_environment() == {}
    with pytest.raises(RelationDataError):
        valkey.ensure_ready()


def test_certificates_install_and_remove_ca(harness: Harness[NetboxCharm]) -> None:
    relation_id = harness.add_relation("certificates", "certificate-provider")
    harness.set_can_connect("app", True)
    container = harness.model.unit.get_container("app")
    container.push(SYSTEM_CA_CERT_PATH, "SYSTEM CA\n", make_dirs=True)
    certificates = get_certificates(harness)
    with patch.object(
        certificates._certificates,
        "get_assigned_certificates",
        return_value=([SimpleNamespace(ca="CUSTOM CA")], None),
    ):
        environment = certificates.gen_environment()
        assert container.pull(CA_CERT_PATH).read() == "SYSTEM CA\n\nCUSTOM CA\n"
        assert environment == {
            "REQUESTS_CA_BUNDLE": CA_CERT_PATH,
            "SSL_CERT_FILE": CA_CERT_PATH,
        }
        with patch.object(certificates, "_on_change") as on_change:
            harness.remove_relation(relation_id)
            on_change.assert_called_once()
        environment = certificates.gen_environment()
        assert not container.exists(CA_CERT_PATH)
        assert environment == {
            "REQUESTS_CA_BUNDLE": SYSTEM_CA_CERT_PATH,
            "SSL_CERT_FILE": SYSTEM_CA_CERT_PATH,
        }


def test_certificates_wait_for_container(harness: Harness[NetboxCharm]) -> None:
    assert get_certificates(harness).gen_environment() == {}


@pytest.mark.parametrize("endpoints", [[], ["redis"], ["valkey"], ["redis", "valkey"]])
def test_requires_exactly_one_cache(harness: Harness[NetboxCharm], endpoints: list[str]) -> None:
    for endpoint in endpoints:
        harness.add_relation(endpoint, f"{endpoint}-provider")
    with (
        patch.object(paas_charm.django.Charm, "is_ready", return_value=True),
        patch.object(harness.charm, "_stop_all_and_set_blocked") as stop,
    ):
        assert harness.charm.is_ready() is (len(endpoints) == 1)
        assert stop.call_count == (0 if len(endpoints) == 1 else 1)


def test_framework_readiness_is_preserved(harness: Harness[NetboxCharm]) -> None:
    with patch.object(paas_charm.django.Charm, "is_ready", return_value=False):
        assert not harness.charm.is_ready()
