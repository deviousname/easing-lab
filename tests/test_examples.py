import os
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    find_spec("pygame") is None,
    reason='examples require the "app" extra',
)


def test_easing_gauntlet_headless_smoke(tmp_path):
    screenshot = tmp_path / "easing-gauntlet.png"
    environment = os.environ.copy()
    environment.update(
        {
            "PYGAME_HIDE_SUPPORT_PROMPT": "1",
            "SDL_VIDEODRIVER": "dummy",
            "SDL_AUDIODRIVER": "dummy",
        }
    )
    result = subprocess.run(
        [
            sys.executable,
            "examples/easing_gauntlet.py",
            "--frames",
            "240",
            "--seed",
            "11",
            "--screenshot",
            str(screenshot),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert screenshot.is_file()
    assert screenshot.stat().st_size > 10_000
    assert Path(screenshot).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
