# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tests for the unprivileged Supercronic scheduler."""

from fnmatch import fnmatch
from pathlib import Path
from unittest.mock import Mock

import ops.pebble
import pytest
import yaml
from paas_charm.app import App, WorkloadConfig

ROOT = Path(__file__).resolve().parents[2]


def test_scheduler_runs_without_root_or_python_runner():
    recipe = yaml.safe_load((ROOT / "netbox/rockcraft.yaml").read_text())
    service = recipe["services"]["cron-scheduler"]

    assert service["command"] == "/bin/supercronic /etc/netbox/crontab"
    assert service["user"] == "_daemon_"
    assert "user-id" not in service
    assert "group-id" not in service
    assert "run-user" not in recipe
    assert service["working-dir"] == "/app"
    assert service["startup"] == "enabled"
    assert "cron-accounts" not in recipe["parts"]
    assert recipe["parts"]["cron"] == {
        "plugin": "go",
        "source": "https://github.com/aptible/supercronic.git",
        "source-tag": "v0.2.51",
        "build-snaps": ["go/latest/stable"],
    }
    assert recipe["parts"]["cron-tasks"] == {
        "plugin": "dump",
        "source": "cron.d",
        "organize": {"crontab": "etc/netbox/crontab"},
        "permissions": [
            {"path": "etc", "mode": "755"},
            {"path": "etc/netbox", "mode": "755"},
            {"path": "etc/netbox/crontab", "mode": "644"},
        ],
    }
    assert recipe["services"]["netbox-rq-worker"]["user"] == "_daemon_"
    assert "APScheduler" not in (ROOT / "patches/requirements.patch").read_text()
    assert not (ROOT / "scheduler.py").exists()


def test_schedule_paths_are_readable_and_traversable(tmp_path: Path):
    recipe = yaml.safe_load((ROOT / "netbox/rockcraft.yaml").read_text())
    permissions = recipe["parts"]["cron-tasks"]["permissions"]
    directories = [tmp_path / "etc", tmp_path / "etc/netbox"]
    directories[-1].mkdir(parents=True)
    crontab = directories[-1] / "crontab"
    content = (ROOT / "cron.d/crontab").read_text()
    crontab.write_text(content)

    try:
        for path in [crontab, *reversed(directories)]:
            for permission in permissions:
                if fnmatch(str(path.relative_to(tmp_path)), permission.get("path", "*")):
                    path.chmod(int(permission["mode"], 8))

        for directory in directories:
            assert directory.stat().st_mode & 0o777 == 0o755
        assert crontab.stat().st_mode & 0o777 == 0o644
        assert crontab.read_text() == content
    finally:
        for directory in directories:
            directory.chmod(0o755)


@pytest.mark.parametrize("unit_number", [0, 1])
def test_framework_supplies_environment_only_on_scheduler_unit(
    monkeypatch: pytest.MonkeyPatch, unit_number: int
):
    services = yaml.safe_load((ROOT / "netbox/rockcraft.yaml").read_text())["services"]
    services["django"] = {"command": "gunicorn"}
    container = Mock()
    container.exists.return_value = False
    container.get_plan.return_value = ops.pebble.Plan(yaml.safe_dump({"services": services}))
    config = WorkloadConfig(
        framework="django",
        port=8000,
        base_dir=Path("/app"),
        app_dir=Path("/app"),
        state_dir=Path("/state"),
        service_name="django",
        unit_name=f"netbox/{unit_number}",
    )
    app = App(
        container=container,
        charm_state=Mock(),
        workload_config=config,
        database_migration=Mock(),
    )
    environment = {"DJANGO_SECRET_KEY": "test-key", "POSTGRESQL_DB_HOSTNAME": "database"}
    monkeypatch.setattr(app, "gen_environment", Mock(return_value=environment))

    services = ops.pebble.Layer(app._app_layer()).services
    scheduler = services["cron-scheduler"]
    if unit_number == 0:
        assert scheduler.startup == "enabled"
        assert scheduler.environment == services["django"].environment == environment
    else:
        assert scheduler.startup == "disabled"


def test_schedules_use_utc_and_inherit_the_service_environment():
    crontab = (ROOT / "cron.d/crontab").read_text()
    entries = [line for line in crontab.splitlines() if line and not line.startswith("#")]

    assert entries == [
        "CRON_TZ=UTC",
        "0 0 * * * /bin/python3 manage.py housekeeping",
        "*/5 * * * * /bin/python3 manage.py syncdatasource --all",
    ]
    assert crontab.endswith("\n")
