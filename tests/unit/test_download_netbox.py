# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tests for failures during NetBox rock source preparation."""

import os
import subprocess
import tarfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "download_netbox.sh"


@pytest.mark.parametrize("failed_command", ["wget", "tar", "patch"])
def test_source_preparation_stops_on_failure(tmp_path: Path, failed_command: str):
    """
    arrange: Replace download, extraction, and patch commands with controlled stubs.
    act: Run source preparation with one command failing.
    assert: Return the failure without updating the recipe or continuing preparation.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "calls"
    for command in ("wget", "tar", "patch"):
        stub = bin_dir / command
        stub.write_text(
            "#!/bin/bash\n"
            f'echo {command} >> "$CALLS"\n'
            f'if [ "{command}" = "$FAILED_COMMAND" ]; then exit 42; fi\n'
        )
        stub.chmod(0o755)
    netbox = tmp_path / "netbox"
    netbox.mkdir()
    recipe = netbox / "rockcraft.yaml"
    recipe.write_text('version: "original"\n')
    patches = tmp_path / "patches"
    patches.mkdir()
    (patches / "settings.patch").touch()
    (patches / "requirements.patch").touch()

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=tmp_path,
        env={
            **os.environ,
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "CALLS": str(calls),
            "FAILED_COMMAND": failed_command,
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 42, result.stderr
    expected = ["wget", "tar", "patch"]
    assert calls.read_text().splitlines() == expected[: expected.index(failed_command) + 1]
    assert recipe.read_text() == 'version: "original"\n'
    assert not (netbox / "netbox/scheduler.py").exists()


def test_source_preparation_includes_scheduler(tmp_path: Path):
    """Prepare a local NetBox archive with the real requirements patch and scheduler."""
    root = SCRIPT.parent
    source = tmp_path / "source"
    (source / "netbox/netbox").mkdir(parents=True)
    (source / "requirements.txt").write_text(
        "# requirements\n" * 43 + "tablib==3.10.0\ntzdata==2026.5\nzensical==0.0.69\n"
    )
    (source / "upgrade.sh").write_text("#!/bin/bash\n")
    archive = tmp_path / "archive.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(source, arcname="netbox")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    wget = bin_dir / "wget"
    wget.write_text('#!/bin/bash\ncp "$ARCHIVE" "${1##*/}"\n')
    wget.chmod(0o755)
    (tmp_path / "netbox").mkdir()
    (tmp_path / "netbox/rockcraft.yaml").write_text('version: "original"\n')
    (tmp_path / "patches").mkdir()
    (tmp_path / "patches/settings.patch").touch()
    (tmp_path / "patches/requirements.patch").write_text(
        (root / "patches/requirements.patch").read_text()
    )
    for name in ("scheduler.py", "configuration.py"):
        (tmp_path / name).write_text((root / name).read_text())

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=tmp_path,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "ARCHIVE": str(archive)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "netbox/netbox/scheduler.py").read_text() == (
        root / "scheduler.py"
    ).read_text()
    assert (tmp_path / "netbox/netbox/netbox/configuration.py").exists()
    assert (tmp_path / "netbox/migrate.sh").exists()
    assert "APScheduler==3.11.3" in (tmp_path / "netbox/requirements.txt").read_text()
    assert not (tmp_path / "netbox/cron.d").exists()
