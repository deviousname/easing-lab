import os
import subprocess
import sys
from pathlib import Path


def test_library_import_has_no_pygame_initialization_side_effects():
    command = (
        "import pygame; assert not pygame.get_init(); "
        "import easing_lab; assert not pygame.get_init()"
    )
    environment = os.environ.copy()
    environment["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", command],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert result.returncode == 0, result.stderr


def test_standalone_headless_screenshot_smoke(tmp_path):
    screenshot = tmp_path / "smoke.png"
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
            "-m",
            "easing_lab",
            "--size",
            "1180x760",
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
