# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tests for the NetBox cron daemon and unprivileged jobs."""

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_cron_daemon_runs_as_root():
    recipe = yaml.safe_load((ROOT / "netbox/rockcraft.yaml").read_text())
    service = recipe["services"]["cron-scheduler"]

    assert service["command"] == "/usr/sbin/cron -f"
    assert service["user"] == "root"
    assert service["startup"] == "enabled"
    assert recipe["parts"]["cron"] == {"plugin": "nil", "stage-packages": ["cron"]}
    assert recipe["parts"]["cron-tasks"]["organize"] == {
        "housekeeping": "etc/cron.d/housekeeping",
        "syncdatasource": "etc/cron.d/syncdatasource",
    }
    assert recipe["services"]["netbox-rq-worker"]["user"] == "_daemon_"


@pytest.mark.parametrize(
    ("name", "schedule", "command"),
    [
        ("housekeeping", "0 0 * * *", "housekeeping"),
        ("syncdatasource", "*/5 * * * *", "syncdatasource --all"),
    ],
)
def test_cron_jobs_use_workload_user_and_environment(name: str, schedule: str, command: str):
    crontab = (ROOT / "cron.d" / name).read_text()
    jobs = [line for line in crontab.splitlines() if line and not line.startswith("#")]

    assert jobs == [
        f"{schedule} root PEBBLE_SOCKET=/charm/container/pebble.socket "
        "pebble exec --user=_daemon_ -w=/app --context=django -- "
        f'/bin/python3 manage.py {command} >> "/proc/$(cat /run/crond.pid)/fd/2" 2>&1',
    ]
    assert crontab.endswith("\n")
