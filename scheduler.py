# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Run scheduled NetBox maintenance without elevated privileges."""

import logging
import signal
import subprocess
import sys

from apscheduler.schedulers.blocking import BlockingScheduler


def run_management_command(*arguments: str) -> None:
    """Run a management command with the scheduler's environment and log streams."""
    subprocess.run([sys.executable, "manage.py", *arguments], check=True)


def create_scheduler() -> BlockingScheduler:
    """Schedule maintenance in UTC, allowing only one instance of each job."""
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        run_management_command,
        "cron",
        id="housekeeping",
        name="housekeeping",
        args=("housekeeping",),
        hour=0,
        minute=0,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60,
    )
    scheduler.add_job(
        run_management_command,
        "cron",
        id="syncdatasource",
        name="syncdatasource",
        args=("syncdatasource", "--all"),
        minute="*/5",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60,
    )
    return scheduler


def main() -> None:
    """Run until Pebble stops the service, finishing any active maintenance jobs."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    scheduler = create_scheduler()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown(wait=True)


if __name__ == "__main__":
    main()
