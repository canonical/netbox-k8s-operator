# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tests for the unprivileged NetBox maintenance scheduler."""

import importlib.metadata
import importlib.util
import json
import os
import signal
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from threading import Event, Thread
from types import ModuleType
from unittest.mock import Mock

import ops.pebble
import pytest
import yaml
from apscheduler.triggers.interval import IntervalTrigger
from paas_charm.app import App, WorkloadConfig

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def scheduler_module(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    spec = importlib.util.spec_from_file_location("netbox_scheduler", ROOT / "scheduler.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


def test_scheduler_runs_without_root_or_cron():
    recipe = yaml.safe_load((ROOT / "netbox/rockcraft.yaml").read_text())
    service = recipe["services"]["cron-scheduler"]

    assert service["command"] == "/bin/python3 /app/scheduler.py"
    assert service["user"] == "_daemon_"
    assert "user-id" not in service
    assert "group-id" not in service
    assert "run-user" not in recipe
    assert service["working-dir"] == "/app"
    assert service["startup"] == "enabled"
    assert not {"cron", "cron-accounts", "cron-tasks"} & recipe["parts"].keys()
    assert recipe["services"]["netbox-rq-worker"]["user"] == "_daemon_"
    assert (
        f"+APScheduler=={importlib.metadata.version('APScheduler')}"
        in (ROOT / "patches/requirements.patch").read_text().splitlines()
    )


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


@pytest.mark.parametrize(
    ("job_id", "arguments", "next_run"),
    [
        ("housekeeping", ("housekeeping",), datetime(2026, 10, 23, tzinfo=UTC)),
        ("syncdatasource", ("syncdatasource", "--all"), datetime(2026, 10, 22, 12, 5, tzinfo=UTC)),
    ],
)
def test_schedules_and_overlap_policy(
    scheduler_module: ModuleType, job_id: str, arguments: tuple[str, ...], next_run: datetime
):
    scheduler = scheduler_module.create_scheduler()
    job = scheduler.get_job(job_id)
    assert job is not None
    assert len(scheduler.get_jobs()) == 2
    assert str(scheduler.timezone) == "UTC"
    assert job.args == arguments
    assert job.max_instances == 1
    assert job.coalesce is True
    assert job.misfire_grace_time == 60
    assert (
        job.trigger.get_next_fire_time(None, datetime(2026, 10, 22, 12, 1, tzinfo=UTC)) == next_run
    )


def test_command_inherits_identity_environment_directory_and_output(
    scheduler_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DJANGO_SECRET_KEY", "test-key")
    (tmp_path / "manage.py").write_text(
        "import json, os, sys\n"
        "print(json.dumps([sys.argv[1:], os.getcwd(), "
        "os.environ['DJANGO_SECRET_KEY'], os.getuid()]))\n"
        "print('command stderr', file=sys.stderr)\n"
    )

    scheduler_module.run_management_command("syncdatasource", "--all")

    output = capfd.readouterr()
    assert json.loads(output.out) == [
        ["syncdatasource", "--all"],
        str(tmp_path),
        "test-key",
        os.getuid(),
    ]
    assert output.err == "command stderr\n"


def test_command_failure_is_not_swallowed(
    scheduler_module: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "manage.py").write_text("raise SystemExit(7)\n")

    with pytest.raises(subprocess.CalledProcessError) as error:
        scheduler_module.run_management_command("housekeeping")

    assert error.value.returncode == 7


def test_failed_job_is_logged_and_runs_again(
    scheduler_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "manage.py").write_text(
        "from pathlib import Path\n"
        "marker = Path('attempted')\n"
        "if not marker.exists():\n"
        "    marker.touch()\n"
        "    raise SystemExit(7)\n"
    )
    completed = Event()

    def run(*arguments: str):
        scheduler_module.run_management_command(*arguments)
        completed.set()

    scheduler = scheduler_module.create_scheduler()
    scheduler.modify_job(
        "syncdatasource",
        func=run,
        trigger=IntervalTrigger(seconds=1),
        next_run_time=datetime.now(UTC),
    )
    thread = Thread(target=scheduler.start, daemon=True)
    thread.start()
    try:
        assert completed.wait(timeout=5), "Scheduler did not recover after the failed command"
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=True)
        thread.join(timeout=5)

    assert not thread.is_alive()
    assert "raised an exception" in caplog.text
    assert "exit status 7" in caplog.text


@pytest.mark.parametrize("interruption", [KeyboardInterrupt, SystemExit])
def test_scheduler_shuts_down_on_stop(
    scheduler_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    interruption: type[BaseException],
):
    scheduler = Mock()
    scheduler.start.side_effect = interruption
    monkeypatch.setattr(scheduler_module, "create_scheduler", Mock(return_value=scheduler))
    handler = Mock()
    monkeypatch.setattr(scheduler_module.signal, "signal", handler)

    scheduler_module.main()

    handler.assert_called_once()
    assert handler.call_args.args[0] == signal.SIGTERM
    scheduler.shutdown.assert_called_once_with(wait=True)
