# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tests for the rootless NetBox scheduler configuration."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_scheduler_runs_as_workload_user():
    recipe = yaml.safe_load((ROOT / "netbox/rockcraft.yaml").read_text())
    service = recipe["services"]["cron-scheduler"]

    assert service["command"] == "/bin/supercronic /etc/netbox/crontab"
    assert service["user"] == "_daemon_"
    assert service["working-dir"] == "/app"
    assert service["startup"] == "enabled"
    assert recipe["parts"]["cron"]["plugin"] == "go"
    assert recipe["parts"]["cron-tasks"]["organize"] == {"crontab": "etc/netbox/crontab"}


def test_scheduler_jobs_do_not_require_root_or_pebble_exec():
    jobs = [
        line
        for line in (ROOT / "cron.d/crontab").read_text().splitlines()
        if line and not line.startswith("#")
    ]

    assert jobs == [
        "0 0 * * * /bin/python3 manage.py housekeeping",
        "*/5 * * * * /bin/python3 manage.py syncdatasource --all",
    ]
