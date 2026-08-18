"""Interactive Pygame designer for the Easing Lab package."""

from __future__ import annotations

import argparse
import json
import math
import os
from contextlib import suppress
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

try:
    import pygame
except ModuleNotFoundError as exc:
    if exc.name != "pygame":
        raise
    raise SystemExit(
        'The Easing Lab designer needs Pygame. Install it with:\n  pip install "easing-lab[app]"'
    ) from None

from . import __version__
from .core import (
    PRESETS,
    Curve,
    InvalidCurveError,
    Preset,
    clamp,
    curve_from_preset,
    ping_pong,
    preset_document,
)

DEFAULT_SIZE = (1440, 960)
MIN_SIZE = (1180, 760)
GRAPH_Y_MIN = -0.38
GRAPH_Y_MAX = 1.38

BG = (18, 20, 26)
PANEL = (28, 31, 40)
PANEL_2 = (34, 38, 48)
GRID = (67, 74, 92)
TEXT = (238, 241, 247)
MUTED = (158, 166, 184)
ACCENT = (103, 210, 255)
GREEN = (117, 230, 166)
YELLOW = (255, 205, 104)
PINK = (255, 126, 174)
PURPLE = (177, 143, 255)
ORANGE = (255, 159, 91)
RED = (255, 112, 112)
WHITE = (255, 255, 255)

PRESET_COLORS = {
    "linear": MUTED,
    "sine_in_out": ACCENT,
    "smoothstep": GREEN,
    "smootherstep": YELLOW,
    "cubic_in_out": PURPLE,
    "quint_in_out": ORANGE,
    "back_in_out": PINK,
    "bounce_in_out": RED,
    "elastic_in_out": (132, 225, 255),
}


def _parse_size(value: str) -> tuple[int, int]:
    try:
        width_text, height_text = value.lower().split("x", 1)
        width = int(width_text)
        height = int(height_text)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("size must look like 1440x960") from exc
    if width < MIN_SIZE[0] or height < MIN_SIZE[1]:
        raise argparse.ArgumentTypeError(f"minimum designer size is {MIN_SIZE[0]}x{MIN_SIZE[1]}")
    return width, height


def _safe_filename(name: str) -> str:
    stem = "".join(character.lower() if character.isalnum() else "_" for character in name)
    return stem.strip("_") or "easing"


def _choose_json_path(*, save: bool, suggested: str = "easing.json") -> Path | None:
    """Use the native Tk dialog, with a predictable fallback for export."""

    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        with suppress(Exception):
            root.attributes("-topmost", True)
        if save:
            filename = filedialog.asksaveasfilename(
                title="Export easing JSON",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialfile=suggested,
            )
        else:
            filename = filedialog.askopenfilename(
                title="Import easing JSON",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            )
        root.destroy()
        return Path(filename) if filename else None
    except Exception:
        return Path.cwd() / suggested if save else None


class EasingLabApp:
    """Own the complete Pygame lifecycle and interactive designer state."""

    def __init__(self, size: tuple[int, int] = DEFAULT_SIZE) -> None:
        pygame.init()
        pygame.display.set_caption("Easing Lab — motion, projection, and editable curves")
        self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18)
        self.font_small = pygame.font.SysFont("consolas", 14)
        self.font_tiny = pygame.font.SysFont("consolas", 12)
        self.font_big = pygame.font.SysFont("consolas", 25, bold=True)
        self.font_huge = pygame.font.SysFont("consolas", 34, bold=True)

        self.presets = tuple(PRESETS.values())
        self.curve_points = {
            preset.key: [list(point) for point in curve_from_preset(preset).points]
            for preset in self.presets
            if preset.editable
        }
        self._curve_cache: dict[str, Curve] = {}

        self.elapsed = 0.0
        self.paused = False
        self.speed = 1.0
        self.selected_index = next(
            index for index, preset in enumerate(self.presets) if preset.key == "bounce_in_out"
        )
        self.selected_point: int | None = None
        self.dragging_point = False
        self.add_mode = False
        self.status = ""
        self.status_until = 0
        self.running = True

    @property
    def selected_preset(self) -> Preset:
        return self.presets[self.selected_index]

    def close(self) -> None:
        """Release all Pygame modules initialized by the app."""

        pygame.quit()

    def _points(self, preset: Preset | None = None) -> list[list[float]]:
        return self.curve_points[(preset or self.selected_preset).key]

    def _invalidate_curve(self, preset: Preset | None = None) -> None:
        self._curve_cache.pop((preset or self.selected_preset).key, None)

    def _curve(self, preset: Preset) -> Curve:
        curve = self._curve_cache.get(preset.key)
        if curve is None:
            curve = Curve(self.curve_points[preset.key])
            self._curve_cache[preset.key] = curve
        return curve

    def easing_value(self, preset: Preset, t: float) -> float:
        if not preset.editable:
            return preset(t)
        return self._curve(preset)(t)

    def _show_status(self, message: str, *, milliseconds: int = 5000) -> None:
        self.status = message
        self.status_until = pygame.time.get_ticks() + milliseconds

    def reset_selected(self) -> None:
        preset = self.selected_preset
        if not preset.editable:
            return
        self.curve_points[preset.key] = [list(point) for point in curve_from_preset(preset).points]
        self._invalidate_curve(preset)
        self.selected_point = None
        self.add_mode = False
        self._show_status(f"Reset {preset.name}")

    def export_selected(self, path: Path | None = None) -> Path | None:
        preset = self.selected_preset
        if path is None:
            path = _choose_json_path(
                save=True,
                suggested=f"{_safe_filename(preset.name)}.json",
            )
        if path is None:
            self._show_status("Export cancelled")
            return None

        payload = (
            self._curve(preset).to_dict(name=preset.name, subtitle=preset.subtitle)
            if preset.editable
            else preset_document(preset)
        )
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            self._show_status(f"Export failed: {exc}")
            return None
        self._show_status(f"Saved {path.name}")
        return path

    def import_curve(self, path: Path | None = None) -> bool:
        preset = self.selected_preset
        if not preset.editable:
            self._show_status("Select an editable curve before importing")
            return False
        if path is None:
            path = _choose_json_path(save=False)
        if path is None:
            self._show_status("Import cancelled")
            return False
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise InvalidCurveError("document must contain a JSON object")
            curve = Curve.from_dict(payload)
        except (OSError, json.JSONDecodeError, InvalidCurveError) as exc:
            self._show_status(f"Import failed: {exc}", milliseconds=7000)
            return False

        self.curve_points[preset.key] = [list(point) for point in curve.points]
        self._curve_cache[preset.key] = curve
        self.selected_point = None
        self.add_mode = False
        self._show_status(f"Loaded {path.name} into {preset.name}")
        return True

    def _text(
        self,
        text: str,
        position: tuple[int, int],
        color: tuple[int, int, int] = TEXT,
        font: pygame.font.Font | None = None,
    ) -> None:
        self.screen.blit((font or self.font).render(text, True, color), position)

    @staticmethod
    def _rounded_panel(
        surface: pygame.Surface,
        rect: pygame.Rect,
        fill: tuple[int, int, int] = PANEL,
        radius: int = 16,
        border: tuple[int, int, int] | None = None,
        width: int = 1,
    ) -> None:
        pygame.draw.rect(surface, fill, rect, border_radius=radius)
        if border:
            pygame.draw.rect(surface, border, rect, width, border_radius=radius)

    @staticmethod
    def graph_to_screen(rect: pygame.Rect, t: float, value: float) -> tuple[int, int]:
        x = rect.x + int(rect.width * t)
        normalized = (value - GRAPH_Y_MIN) / (GRAPH_Y_MAX - GRAPH_Y_MIN)
        y = rect.y + int(rect.height * (1.0 - normalized))
        return x, y

    @staticmethod
    def screen_to_graph(rect: pygame.Rect, x: int, y: int) -> tuple[float, float]:
        t = clamp((x - rect.x) / max(1, rect.width), 0.0, 1.0)
        normalized = 1.0 - (y - rect.y) / max(1, rect.height)
        value = GRAPH_Y_MIN + normalized * (GRAPH_Y_MAX - GRAPH_Y_MIN)
        return t, clamp(value, GRAPH_Y_MIN, GRAPH_Y_MAX)

    def _draw_curve(
        self,
        rect: pygame.Rect,
        preset: Preset,
        *,
        t_now: float | None = None,
        points: list[list[float]] | None = None,
        selected_point: int | None = None,
    ) -> None:
        color = PRESET_COLORS[preset.key]
        for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
            x = rect.x + int(rect.width * fraction)
            pygame.draw.line(self.screen, (45, 49, 61), (x, rect.top), (x, rect.bottom), 1)
        for value in (0.0, 0.5, 1.0):
            _, y = self.graph_to_screen(rect, 0.0, value)
            line_color = GRID if value in (0.0, 1.0) else (45, 49, 61)
            pygame.draw.line(self.screen, line_color, (rect.left, y), (rect.right, y), 1)

        curve_pixels = []
        for index in range(121):
            t = index / 120.0
            value = clamp(self.easing_value(preset, t), GRAPH_Y_MIN, GRAPH_Y_MAX)
            curve_pixels.append(self.graph_to_screen(rect, t, value))
        pygame.draw.lines(self.screen, color, False, curve_pixels, 2)

        if points is not None:
            for index, (t, value) in enumerate(points):
                x, y = self.graph_to_screen(rect, t, value)
                radius = 7 if index == selected_point else 5
                fill = WHITE if index == selected_point else PANEL_2
                pygame.draw.circle(self.screen, fill, (x, y), radius)
                pygame.draw.circle(self.screen, color, (x, y), radius, 2)

        if t_now is not None:
            value = clamp(self.easing_value(preset, t_now), GRAPH_Y_MIN, GRAPH_Y_MAX)
            pygame.draw.circle(self.screen, WHITE, self.graph_to_screen(rect, t_now, value), 4)

    def _draw_track(self, rect: pygame.Rect, value: float, color: tuple[int, int, int]) -> None:
        center_y = rect.centery
        pygame.draw.line(self.screen, GRID, (rect.left, center_y), (rect.right, center_y), 3)
        pygame.draw.circle(self.screen, (74, 81, 100), (rect.left, center_y), 5)
        pygame.draw.circle(self.screen, (74, 81, 100), (rect.right, center_y), 5)
        x = rect.left + int(rect.width * value)
        pygame.draw.circle(self.screen, color, (x, center_y), 9)
        pygame.draw.circle(self.screen, WHITE, (x, center_y), 9, 2)

    def _draw_button(
        self,
        rect: pygame.Rect,
        text: str,
        *,
        active: bool = False,
        enabled: bool = True,
    ) -> None:
        fill = (53, 61, 75) if enabled else (39, 42, 50)
        border = ACCENT if active else (76, 84, 101)
        self._rounded_panel(self.screen, rect, fill, 8, border)
        color = TEXT if enabled else (103, 108, 120)
        rendered = self.font_tiny.render(text, True, color)
        self.screen.blit(
            rendered,
            (rect.centerx - rendered.get_width() // 2, rect.centery - rendered.get_height() // 2),
        )

    def _draw_easing_card(
        self,
        rect: pygame.Rect,
        preset: Preset,
        t: float,
        *,
        selected: bool,
    ) -> None:
        color = PRESET_COLORS[preset.key]
        border = color if selected else (46, 51, 63)
        self._rounded_panel(self.screen, rect, PANEL, 14, border, 2 if selected else 1)
        self._text(preset.name, (rect.x + 14, rect.y + 10))
        self._text(preset.subtitle, (rect.x + 14, rect.y + 32), MUTED, self.font_tiny)

        tag = "EDITABLE" if preset.editable else "EXACT"
        rendered = self.font_tiny.render(tag, True, color)
        self.screen.blit(rendered, (rect.right - rendered.get_width() - 12, rect.y + 12))

        graph = pygame.Rect(rect.x + 14, rect.y + 56, rect.width - 28, max(66, rect.height - 118))
        self._draw_curve(graph, preset, t_now=t)
        track = pygame.Rect(rect.x + 18, rect.bottom - 48, rect.width - 36, 30)
        self._draw_track(track, self.easing_value(preset, t), color)

    def _draw_projection_panel(
        self,
        rect: pygame.Rect,
        circle_phase: float,
        *,
        forward: bool,
    ) -> None:
        self._rounded_panel(self.screen, rect, PANEL, 18, (49, 55, 68))
        self._text(
            "Circle → 1D projection",
            (rect.x + 18, rect.y + 14),
            TEXT,
            self.font_big,
        )
        self._text(
            "The hand completes 360°, then reverses through 360°.",
            (rect.x + 18, rect.y + 44),
            MUTED,
            self.font_tiny,
        )

        radius = int(clamp((rect.height - 105) / 2, 46, 72))
        center_x = rect.x + 24 + radius
        center_y = rect.y + 67 + radius
        pygame.draw.circle(self.screen, GRID, (center_x, center_y), radius, 2)
        pygame.draw.line(
            self.screen,
            GRID,
            (center_x - radius, center_y),
            (center_x + radius, center_y),
            1,
        )
        pygame.draw.line(
            self.screen,
            GRID,
            (center_x, center_y - radius),
            (center_x, center_y + radius),
            1,
        )

        theta = pygame.math.Vector2(1, 0).rotate_rad(math.pi + math.tau * circle_phase)
        hand_x = center_x + int(radius * theta.x)
        hand_y = center_y - int(radius * theta.y)
        pygame.draw.line(self.screen, ACCENT, (center_x, center_y), (hand_x, hand_y), 3)
        pygame.draw.circle(self.screen, ACCENT, (hand_x, hand_y), 9)
        pygame.draw.circle(self.screen, WHITE, (hand_x, hand_y), 9, 2)

        axis_x0 = rect.x + 2 * radius + 66
        axis_x1 = rect.right - 26
        pygame.draw.line(self.screen, GRID, (axis_x0, center_y), (axis_x1, center_y), 3)
        pygame.draw.circle(self.screen, (74, 81, 100), (axis_x0, center_y), 5)
        pygame.draw.circle(self.screen, (74, 81, 100), (axis_x1, center_y), 5)
        projected = 0.5 + 0.5 * theta.x
        shadow_x = axis_x0 + int((axis_x1 - axis_x0) * projected)
        pygame.draw.line(self.screen, (80, 93, 112), (hand_x, hand_y), (shadow_x, center_y), 1)
        pygame.draw.circle(self.screen, ACCENT, (shadow_x, center_y), 10)
        pygame.draw.circle(self.screen, WHITE, (shadow_x, center_y), 10, 2)

        direction = "forward CW" if forward else "reverse CCW"
        self._text(direction, (rect.x + 50, rect.bottom - 62), ACCENT, self.font_tiny)
        self._text("projected x", (axis_x0 + 28, rect.bottom - 62), MUTED, self.font_tiny)
        self._text(
            "A → B → A per turn; reverse at A with zero projected speed.",
            (rect.x + 18, rect.bottom - 34),
            MUTED,
            self.font_tiny,
        )

    @staticmethod
    def _editor_hits(rect: pygame.Rect) -> dict[str, pygame.Rect]:
        return {
            "reset": pygame.Rect(rect.x + 18, rect.y + 88, 104, 28),
            "add": pygame.Rect(rect.x + 130, rect.y + 88, 88, 28),
            "remove": pygame.Rect(rect.x + 226, rect.y + 88, 108, 28),
            "import": pygame.Rect(rect.x + 18, rect.y + 122, 104, 28),
            "export": pygame.Rect(rect.x + 130, rect.y + 122, 104, 28),
            "graph": pygame.Rect(
                rect.x + 18, rect.y + 158, rect.width - 36, max(96, rect.height - 192)
            ),
        }

    def _draw_editor_panel(self, rect: pygame.Rect, t: float) -> dict[str, pygame.Rect]:
        self._rounded_panel(self.screen, rect, PANEL, 18, (49, 55, 68))
        preset = self.selected_preset
        color = PRESET_COLORS[preset.key]
        self._text("Curve editor", (rect.x + 18, rect.y + 13), TEXT, self.font_big)
        self._text(preset.name, (rect.x + 18, rect.y + 45), color, self.font_small)
        helper = (
            "Drag points; endpoints stay pinned at (0,0) and (1,1)."
            if preset.editable
            else "Exact preset: kept locked so the mathematical projection stays exact."
        )
        self._text(helper, (rect.x + 18, rect.y + 65), MUTED, self.font_tiny)

        hits = self._editor_hits(rect)
        points = self._points() if preset.editable else []
        removable = (
            preset.editable
            and self.selected_point is not None
            and 0 < self.selected_point < len(points) - 1
        )
        self._draw_button(hits["reset"], "Reset preset", enabled=preset.editable)
        self._draw_button(hits["add"], "Add point", active=self.add_mode, enabled=preset.editable)
        self._draw_button(hits["remove"], "Remove point", enabled=removable)
        self._draw_button(hits["import"], "Import JSON", enabled=preset.editable)
        self._draw_button(hits["export"], "Export JSON")

        self._draw_curve(
            hits["graph"],
            preset,
            t_now=t,
            points=points if preset.editable else None,
            selected_point=self.selected_point if preset.editable else None,
        )
        self._text("0", (hits["graph"].left - 1, hits["graph"].bottom + 2), MUTED, self.font_tiny)
        self._text("1", (hits["graph"].right - 8, hits["graph"].bottom + 2), MUTED, self.font_tiny)
        self._text(
            "time →",
            (hits["graph"].centerx - 20, hits["graph"].bottom + 2),
            MUTED,
            self.font_tiny,
        )
        if preset.editable and self.add_mode:
            self._text(
                "ADD MODE: click the graph to place a point",
                (rect.x + 244, rect.y + 128),
                YELLOW,
                self.font_tiny,
            )
        return hits

    def _draw_game_examples(self, rect: pygame.Rect, t: float) -> None:
        self._rounded_panel(self.screen, rect, PANEL, 18, (49, 55, 68))
        self._text("Game-feel doodads", (rect.x + 18, rect.y + 12), TEXT, self.font_big)

        row_y = rect.y + 49
        self._text("UI drawer · sine", (rect.x + 18, row_y), MUTED, self.font_tiny)
        background = pygame.Rect(rect.x + 18, row_y + 18, rect.width - 36, 34)
        pygame.draw.rect(self.screen, PANEL_2, background, border_radius=8)
        drawer_width = min(112, background.width // 3)
        drawer_x = background.x + int((background.width - drawer_width) * PRESETS["sine_in_out"](t))
        pygame.draw.rect(
            self.screen,
            ACCENT,
            (drawer_x, background.y + 4, drawer_width, background.height - 8),
            border_radius=7,
        )
        self._text(
            "MENU", (drawer_x + max(8, drawer_width // 3), background.y + 8), BG, self.font_tiny
        )

        preset = self.selected_preset
        color = PRESET_COLORS[preset.key]
        line_y = rect.bottom - 29
        line_x0 = rect.x + 30
        line_x1 = rect.right - 30
        pygame.draw.line(self.screen, GRID, (line_x0, line_y), (line_x1, line_y), 3)
        object_x = line_x0 + int((line_x1 - line_x0) * self.easing_value(preset, t))
        pygame.draw.circle(self.screen, color, (object_x, line_y), 10)
        pygame.draw.circle(self.screen, WHITE, (object_x, line_y), 10, 2)
        self._text(preset.name, (rect.x + 18, line_y - 24), color, self.font_tiny)

    def _compute_layout(
        self,
    ) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect, list[pygame.Rect]]:
        width, height = self.screen.get_size()
        margin = 18
        top = 66
        gap = 12
        content_height = height - top - margin
        left_width = int(clamp(width * 0.34, 420, 470))
        right_x = margin + left_width + gap
        right_width = width - right_x - margin

        projection_height = int(clamp(content_height * 0.35, 220, 300))
        editor_height = int(clamp(content_height * 0.43, 300, 390))
        game_height = content_height - projection_height - editor_height - 2 * gap
        if game_height < 125:
            deficit = 125 - game_height
            projection_reduction = min(deficit, projection_height - 220)
            projection_height -= projection_reduction
            deficit -= projection_reduction
            editor_height -= min(deficit, editor_height - 300)
            game_height = content_height - projection_height - editor_height - 2 * gap

        projection = pygame.Rect(margin, top, left_width, projection_height)
        editor = pygame.Rect(margin, projection.bottom + gap, left_width, editor_height)
        game = pygame.Rect(margin, editor.bottom + gap, left_width, game_height)

        columns = 3
        rows = 3
        card_gap = 12
        card_width = (right_width - card_gap * (columns - 1)) // columns
        card_height = (content_height - card_gap * (rows - 1)) // rows
        cards = []
        for index in range(len(self.presets)):
            row, column = divmod(index, columns)
            cards.append(
                pygame.Rect(
                    right_x + column * (card_width + card_gap),
                    top + row * (card_height + card_gap),
                    card_width,
                    card_height,
                )
            )
        return projection, editor, game, cards

    def _nearest_point(
        self,
        points: list[list[float]],
        graph: pygame.Rect,
        mouse: tuple[int, int],
        radius: int = 12,
    ) -> int | None:
        best_index = None
        best_distance = radius * radius
        for index, (t, value) in enumerate(points):
            x, y = self.graph_to_screen(graph, t, value)
            distance = (mouse[0] - x) ** 2 + (mouse[1] - y) ** 2
            if distance <= best_distance:
                best_index = index
                best_distance = distance
        return best_index

    def _remove_selected_point(self) -> None:
        if not self.selected_preset.editable or self.selected_point is None:
            return
        points = self._points()
        if 0 < self.selected_point < len(points) - 1:
            points.pop(self.selected_point)
            self._invalidate_curve()
            self.selected_point = None

    def _handle_mouse_down(
        self,
        event: pygame.event.Event,
        editor_hits: dict[str, pygame.Rect],
        card_rects: list[pygame.Rect],
    ) -> None:
        mouse = event.pos
        for index, rect in enumerate(card_rects):
            if rect.collidepoint(mouse):
                self.selected_index = index
                self.selected_point = None
                self.dragging_point = False
                self.add_mode = False
                break

        preset = self.selected_preset
        if event.button == 1:
            if editor_hits["reset"].collidepoint(mouse) and preset.editable:
                self.reset_selected()
            elif editor_hits["add"].collidepoint(mouse) and preset.editable:
                self.add_mode = not self.add_mode
                self.selected_point = None
            elif editor_hits["remove"].collidepoint(mouse) and preset.editable:
                self._remove_selected_point()
            elif editor_hits["import"].collidepoint(mouse) and preset.editable:
                self.import_curve()
            elif editor_hits["export"].collidepoint(mouse):
                self.export_selected()
            elif editor_hits["graph"].collidepoint(mouse) and preset.editable:
                points = self._points()
                hit = self._nearest_point(points, editor_hits["graph"], mouse)
                if hit is not None and not self.add_mode:
                    self.selected_point = hit
                    self.dragging_point = True
                elif self.add_mode:
                    t, value = self.screen_to_graph(editor_hits["graph"], *mouse)
                    insert_at = 1
                    while insert_at < len(points) and points[insert_at][0] < t:
                        insert_at += 1
                    low = points[insert_at - 1][0] + 0.012
                    high = points[insert_at][0] - 0.012
                    if low < high:
                        points.insert(insert_at, [clamp(t, low, high), value])
                        self._invalidate_curve()
                        self.selected_point = insert_at
                        self.dragging_point = True
                    self.add_mode = False
                else:
                    self.selected_point = None
        elif event.button == 3 and preset.editable and editor_hits["graph"].collidepoint(mouse):
            points = self._points()
            hit = self._nearest_point(points, editor_hits["graph"], mouse)
            if hit is not None and 0 < hit < len(points) - 1:
                points.pop(hit)
                self._invalidate_curve()
                self.selected_point = None

    def _handle_event(
        self,
        event: pygame.event.Event,
        editor_hits: dict[str, pygame.Rect],
        card_rects: list[pygame.Rect],
    ) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.VIDEORESIZE:
            requested = (max(MIN_SIZE[0], event.w), max(MIN_SIZE[1], event.h))
            self.screen = pygame.display.set_mode(requested, pygame.RESIZABLE)
        elif event.type == pygame.KEYDOWN:
            control = bool(event.mod & pygame.KMOD_CTRL)
            if event.key == pygame.K_ESCAPE:
                self.running = False
            elif event.key == pygame.K_SPACE:
                self.paused = not self.paused
            elif event.key == pygame.K_r and not control:
                self.elapsed = 0.0
            elif event.key == pygame.K_o and control:
                self.import_curve()
            elif event.key == pygame.K_s and control:
                self.export_selected()
            elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.speed = max(0.125, self.speed / 1.25)
            elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                self.speed = min(4.0, self.speed * 1.25)
            elif event.key == pygame.K_1:
                self.speed = 0.5
            elif event.key == pygame.K_2:
                self.speed = 1.0
            elif event.key == pygame.K_3:
                self.speed = 2.0
            elif event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
                self._remove_selected_point()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_mouse_down(event, editor_hits, card_rects)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_point = False
        elif (
            event.type == pygame.MOUSEMOTION
            and self.dragging_point
            and self.selected_point is not None
            and self.selected_preset.editable
        ):
            points = self._points()
            index = self.selected_point
            t, value = self.screen_to_graph(editor_hits["graph"], *event.pos)
            if index == 0:
                points[index] = [0.0, 0.0]
            elif index == len(points) - 1:
                points[index] = [1.0, 1.0]
            else:
                low = points[index - 1][0] + 0.012
                high = points[index + 1][0] - 0.012
                points[index] = [clamp(t, low, high), value]
            self._invalidate_curve()

    def draw(self) -> None:
        projection_rect, editor_rect, game_rect, card_rects = self._compute_layout()
        t = ping_pong(self.elapsed, speed=self.speed, leg_seconds=2.1)
        circle_trip = (self.elapsed * self.speed / 4.2) % 2.0
        circle_phase = circle_trip if circle_trip <= 1.0 else 2.0 - circle_trip

        self.screen.fill(BG)
        self._text("EASING LAB", (24, 16), TEXT, self.font_huge)
        self._text(
            "Space pause · R reset · -/+ speed · Ctrl+O/Ctrl+S import/export",
            (226, 27),
            MUTED,
            self.font_small,
        )
        status_text = (
            f"{'PAUSED' if self.paused else 'PLAYING'}   t={t:0.3f}   speed={self.speed:0.2f}x"
        )
        rendered_status = self.font_small.render(
            status_text,
            True,
            YELLOW if self.paused else GREEN,
        )
        self.screen.blit(
            rendered_status,
            (self.screen.get_width() - rendered_status.get_width() - 24, 27),
        )
        if self.status and pygame.time.get_ticks() < self.status_until:
            self._text(self.status, (226, 48), ACCENT, self.font_tiny)

        self._draw_projection_panel(projection_rect, circle_phase, forward=circle_trip <= 1.0)
        self._draw_editor_panel(editor_rect, t)
        self._draw_game_examples(game_rect, t)
        for index, (preset, rect) in enumerate(zip(self.presets, card_rects, strict=True)):
            self._draw_easing_card(rect, preset, t, selected=index == self.selected_index)
        pygame.display.flip()

    def run(self, *, screenshot: Path | None = None) -> int:
        """Run until the window closes, or render one deterministic screenshot."""

        while self.running:
            delta = self.clock.tick(60) / 1000.0
            _, editor_rect, _, card_rects = self._compute_layout()
            editor_hits = self._editor_hits(editor_rect)
            for event in pygame.event.get():
                self._handle_event(event, editor_hits, card_rects)
            if not self.paused and screenshot is None:
                self.elapsed += delta
            self.draw()
            if screenshot is not None:
                screenshot.parent.mkdir(parents=True, exist_ok=True)
                pygame.image.save(self.screen, screenshot)
                return 0
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="easing-lab",
        description="Explore, edit, import, and export easing curves with Pygame.",
    )
    parser.add_argument(
        "--size",
        type=_parse_size,
        default=DEFAULT_SIZE,
        metavar="WIDTHxHEIGHT",
        help=f"initial window size (minimum {MIN_SIZE[0]}x{MIN_SIZE[1]})",
    )
    parser.add_argument("--open", type=Path, metavar="CURVE.json", help="open a curve at startup")
    parser.add_argument(
        "--screenshot",
        type=Path,
        metavar="IMAGE.png",
        help="render one frame to an image and exit",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    app: EasingLabApp | None = None
    try:
        app = EasingLabApp(args.size)
        if args.open is not None and not app.import_curve(args.open):
            return 2
        if args.screenshot is not None:
            app.elapsed = 1.05
        return app.run(screenshot=args.screenshot)
    except pygame.error as exc:
        print(f"Easing Lab could not start Pygame: {exc}")
        return 1
    finally:
        if app is not None:
            app.close()


if __name__ == "__main__":
    raise SystemExit(main())
