# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tests for failures during NetBox rock source preparation."""

import os
import subprocess
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
    assert not (netbox / "cron.d").exists()
