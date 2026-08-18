"""Render the README animation deterministically from the current app.

The complete visual state repeats every 8.4 seconds: the regular easings finish
two ping-pong cycles while the circle projection finishes one. GIF delays are
stored in centiseconds, so 50 ms (20 fps) and 60 ms (16 2/3 fps) both divide
the loop exactly without a duplicated endpoint frame.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
from PIL import Image, ImageChops, ImageStat

from easing_lab.app import (
    ACCENT,
    BG,
    GRID,
    MUTED,
    PANEL,
    PANEL_2,
    PRESET_COLORS,
    TEXT,
    WHITE,
    EasingLabApp,
)

LOOP_MILLISECONDS = 8_400
SOURCE_SIZE = (1_440, 960)
OUTPUT_SIZE = (1_200, 800)
RESERVED_COLORS = tuple(
    dict.fromkeys(
        (
            BG,
            PANEL,
            PANEL_2,
            GRID,
            TEXT,
            MUTED,
            ACCENT,
            WHITE,
            *PRESET_COLORS.values(),
        )
    )
)


@dataclass(frozen=True, slots=True)
class RenderStats:
    frame_count: int
    duration_ms: int
    colors: int
    mean_channel_error: float
    output_bytes: int


def _size(value: str) -> tuple[int, int]:
    try:
        width_text, height_text = value.lower().split("x", 1)
        width, height = int(width_text), int(height_text)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("size must look like 1200x800") from exc
    if width < 1 or height < 1:
        raise argparse.ArgumentTypeError("width and height must be positive")
    return width, height


def _validate_delay(value: str) -> int:
    try:
        milliseconds = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("frame delay must be an integer") from exc
    if milliseconds < 20 or milliseconds % 10:
        raise argparse.ArgumentTypeError("frame delay must be at least 20 ms and use 10 ms steps")
    if LOOP_MILLISECONDS % milliseconds:
        raise argparse.ArgumentTypeError(
            f"frame delay must divide the {LOOP_MILLISECONDS} ms loop exactly"
        )
    return milliseconds


def _render_rgb(app: EasingLabApp, elapsed: float, output_size: tuple[int, int]) -> Image.Image:
    app.elapsed = elapsed
    app.draw()
    source = Image.frombytes("RGB", app.screen.get_size(), pygame.image.tobytes(app.screen, "RGB"))
    if source.size != output_size:
        source = source.resize(output_size, Image.Resampling.LANCZOS)
    return source


def _global_palette(source: Image.Image, colors: int) -> Image.Image:
    """Build one palette while reserving the UI's semantic accent colors."""

    adaptive_count = colors - len(RESERVED_COLORS)
    if adaptive_count < 2:
        raise ValueError("palette is too small for the reserved UI colors")
    adaptive = source.quantize(
        colors=adaptive_count,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    )
    raw_palette = adaptive.getpalette()
    used_indices = sorted(index for _, index in adaptive.getcolors(maxcolors=256) or [])
    adaptive_colors = [tuple(raw_palette[index * 3 : index * 3 + 3]) for index in used_indices]

    combined = list(RESERVED_COLORS)
    combined.extend(color for color in adaptive_colors if color not in combined)
    combined = combined[:colors]
    combined.extend([(0, 0, 0)] * (colors - len(combined)))

    flattened = [channel for color in combined for channel in color]
    flattened.extend([0] * (768 - len(flattened)))
    palette = Image.new("P", (1, 1))
    palette.putpalette(flattened)
    return palette


def render_gif(
    output: Path,
    *,
    frame_duration_ms: int,
    colors: int,
    output_size: tuple[int, int],
) -> RenderStats:
    frame_count = LOOP_MILLISECONDS // frame_duration_ms
    app = EasingLabApp(SOURCE_SIZE)
    frames: list[Image.Image] = []
    channel_error_total = 0.0

    try:
        first_rgb = _render_rgb(app, 0.0, output_size)
        palette = _global_palette(first_rgb, colors)

        for index in range(frame_count):
            rgb = (
                first_rgb
                if index == 0
                else _render_rgb(
                    app,
                    index * frame_duration_ms / 1_000.0,
                    output_size,
                )
            )
            quantized = rgb.quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG)
            difference = ImageChops.difference(rgb, quantized.convert("RGB"))
            channel_error_total += sum(ImageStat.Stat(difference).mean) / 3.0
            frames.append(quantized)

        # A mathematical loop is not enough: assert the app really returns to
        # the identical rendered pixels at the exact boundary.
        loop_boundary = _render_rgb(app, LOOP_MILLISECONDS / 1_000.0, output_size)
        if ImageChops.difference(first_rgb, loop_boundary).getbbox() is not None:
            raise RuntimeError("the rendered app state does not close at 8.4 seconds")
    finally:
        app.close()

    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=frame_duration_ms,
        loop=0,
        disposal=1,
        optimize=True,
    )
    _verify_encoded_gif(output, frames, frame_duration_ms)
    return RenderStats(
        frame_count=frame_count,
        duration_ms=LOOP_MILLISECONDS,
        colors=colors,
        mean_channel_error=channel_error_total / frame_count,
        output_bytes=output.stat().st_size,
    )


def _verify_encoded_gif(
    output: Path,
    expected_frames: list[Image.Image],
    frame_duration_ms: int,
) -> None:
    with Image.open(output) as animation:
        if animation.info.get("loop") != 0:
            raise RuntimeError("encoded GIF is not configured to loop forever")
        if animation.n_frames != len(expected_frames):
            raise RuntimeError(
                f"encoded {animation.n_frames} frames; expected {len(expected_frames)}"
            )
        total_duration = 0
        for index, expected in enumerate(expected_frames):
            animation.seek(index)
            total_duration += animation.info.get("duration", 0)
            actual = animation.convert("RGB")
            if ImageChops.difference(actual, expected.convert("RGB")).getbbox() is not None:
                raise RuntimeError(f"optimized GIF frame {index} decodes incorrectly")
        if total_duration != LOOP_MILLISECONDS:
            raise RuntimeError(
                f"encoded duration is {total_duration} ms; expected {LOOP_MILLISECONDS} ms"
            )
        if any(duration != frame_duration_ms for duration in _frame_durations(animation)):
            raise RuntimeError("encoded GIF contains an inconsistent frame delay")


def _frame_durations(animation: Image.Image) -> list[int]:
    durations = []
    for index in range(animation.n_frames):
        animation.seek(index)
        durations.append(animation.info.get("duration", 0))
    return durations


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        default=Path("docs/easing-lab.gif"),
        help="output GIF path (default: docs/easing-lab.gif)",
    )
    parser.add_argument(
        "--frame-duration-ms",
        type=_validate_delay,
        default=50,
        help="frame delay dividing 8400 ms exactly (default: 50, or 20 fps)",
    )
    parser.add_argument(
        "--colors",
        type=int,
        choices=(128, 256),
        default=256,
        help="global GIF palette size (default: 256)",
    )
    parser.add_argument(
        "--output-size",
        type=_size,
        default=OUTPUT_SIZE,
        metavar="WIDTHxHEIGHT",
        help="final GIF dimensions (default: 1200x800)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stats = render_gif(
        args.output,
        frame_duration_ms=args.frame_duration_ms,
        colors=args.colors,
        output_size=args.output_size,
    )
    fps = 1_000 / args.frame_duration_ms
    print(
        f"Rendered {stats.frame_count} frames at {fps:.3f} fps, "
        f"{stats.duration_ms / 1_000:.1f} s, {stats.colors} colors, "
        f"mean channel error {stats.mean_channel_error:.3f}, "
        f"{stats.output_bytes / 1_000_000:.2f} MB -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
