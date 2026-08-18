"""Easing Gauntlet: a small playable showcase for Easing Lab and Pygame.

Move between lanes to collect motion cores, avoid glitch blocks, and use a
limited safety pulse when the screen gets crowded. Every important movement is
driven by an easing from the public Easing Lab API.
"""

from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pygame

from easing_lab import interpolate, ping_pong

WIDTH: Final = 1100
HEIGHT: Final = 720
FPS: Final = 60
RUN_SECONDS: Final = 45.0
PLAY_RECT: Final = pygame.Rect(38, 112, 762, 570)
PLAYER_Y: Final = PLAY_RECT.bottom - 48
LANE_COUNT: Final = 5
LANE_X: Final = tuple(
    PLAY_RECT.left + (index + 0.5) * PLAY_RECT.width / LANE_COUNT for index in range(LANE_COUNT)
)

INK: Final = (229, 237, 255)
MUTED: Final = (132, 150, 185)
CYAN: Final = (84, 224, 255)
BLUE: Final = (90, 130, 255)
VIOLET: Final = (180, 105, 255)
PINK: Final = (255, 93, 182)
GOLD: Final = (255, 199, 84)
RED: Final = (255, 83, 105)
GREEN: Final = (98, 238, 173)

DROP_EASINGS: Final = (
    ("Sine In", "sine_in", CYAN),
    ("Cubic In", "cubic_in", BLUE),
    ("Quint In", "quint_in", VIOLET),
    ("Back In", "back_in", PINK),
    ("Bounce In", "bounce_in", GOLD),
    ("Elastic In", "elastic_in", GREEN),
)


def _mix(first: tuple[int, int, int], second: tuple[int, int, int], amount: float):
    """Blend two RGB colors with a clamped amount."""

    t = max(0.0, min(1.0, amount))
    return tuple(round(a + (b - a) * t) for a, b in zip(first, second, strict=True))


def _draw_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    color: tuple[int, int, int],
    position: tuple[float, float],
    *,
    center: bool = False,
) -> pygame.Rect:
    image = font.render(text, True, color)
    rect = image.get_rect(center=position) if center else image.get_rect(topleft=position)
    surface.blit(image, rect)
    return rect


@dataclass
class Player:
    lane: int = LANE_COUNT // 2
    x: float = LANE_X[LANE_COUNT // 2]
    start_x: float = LANE_X[LANE_COUNT // 2]
    target_x: float = LANE_X[LANE_COUNT // 2]
    move_age: float = 1.0
    move_seconds: float = 0.22

    def move(self, direction: int) -> None:
        destination = max(0, min(LANE_COUNT - 1, self.lane + direction))
        if destination == self.lane:
            return
        self.start_x = self.x
        self.lane = destination
        self.target_x = LANE_X[destination]
        self.move_age = 0.0

    def update(self, dt: float) -> None:
        self.move_age = min(self.move_seconds, self.move_age + dt)
        progress = self.move_age / self.move_seconds
        self.x = interpolate(self.start_x, self.target_x, progress, "cubic_out")

    @property
    def position(self) -> pygame.Vector2:
        return pygame.Vector2(self.x, PLAYER_Y)


@dataclass
class Drop:
    lane: int
    kind: str
    label: str
    easing: str
    color: tuple[int, int, int]
    duration: float
    age: float = 0.0

    @property
    def progress(self) -> float:
        return min(1.0, self.age / self.duration)

    @property
    def position(self) -> pygame.Vector2:
        y = interpolate(PLAY_RECT.top - 36.0, PLAY_RECT.bottom + 30.0, self.progress, self.easing)
        return pygame.Vector2(LANE_X[self.lane], y)

    @property
    def scale(self) -> float:
        return interpolate(0.15, 1.0, min(1.0, self.age / 0.45), "elastic_out")


@dataclass
class Particle:
    start: pygame.Vector2
    end: pygame.Vector2
    color: tuple[int, int, int]
    age: float = 0.0
    duration: float = 0.65

    @property
    def alive(self) -> bool:
        return self.age < self.duration


class EasingGauntlet:
    """Own the state, rules, and rendering for one game session."""

    def __init__(self, screen: pygame.Surface, *, seed: int = 7) -> None:
        self.screen = screen
        self.rng = random.Random(seed)
        star_rng = random.Random(seed ^ 0xEA51)
        self.stars = [
            (
                star_rng.randrange(WIDTH),
                star_rng.randrange(HEIGHT),
                star_rng.uniform(0.7, 2.4),
                star_rng.uniform(0.0, 3.0),
            )
            for _ in range(85)
        ]
        self.title_font = pygame.font.Font(None, 58)
        self.heading_font = pygame.font.Font(None, 34)
        self.body_font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 19)
        self.reset()

    def reset(self) -> None:
        self.player = Player()
        self.drops: list[Drop] = []
        self.particles: list[Particle] = []
        self.elapsed = 0.0
        self.spawn_in = 0.55
        self.score = 0
        self.combo = 0
        self.shields = 3
        self.pulses = 3
        self.pulse_age: float | None = None
        self.recharge_age = 0.0
        self.score_bump_age = 1.0
        self.hit_flash_age = 1.0
        self.finished_age = 0.0
        self.paused = False
        self.game_over = False

    def move_player(self, direction: int) -> None:
        if not self.paused and not self.game_over:
            self.player.move(direction)

    def activate_pulse(self) -> None:
        if self.paused or self.game_over or self.pulse_age is not None or self.pulses <= 0:
            return
        self.pulses -= 1
        self.pulse_age = 0.0

    def toggle_pause(self) -> None:
        if not self.game_over:
            self.paused = not self.paused

    def _spawn_drop(self) -> None:
        label, easing, color = self.rng.choice(DROP_EASINGS)
        difficulty = min(1.0, self.elapsed / RUN_SECONDS)
        kind = "hazard" if self.rng.random() < 0.2 + 0.15 * difficulty else "core"
        duration = self.rng.uniform(2.75, 3.55) - 0.65 * difficulty
        if kind == "hazard":
            color = RED
        self.drops.append(
            Drop(
                lane=self.rng.randrange(LANE_COUNT),
                kind=kind,
                label=label,
                easing=easing,
                color=color,
                duration=duration,
            )
        )
        self.spawn_in = self.rng.uniform(0.52, 0.82) - 0.18 * difficulty

    def _burst(self, position: pygame.Vector2, color: tuple[int, int, int]) -> None:
        for index in range(12):
            angle = math.tau * index / 12 + self.rng.uniform(-0.12, 0.12)
            distance = self.rng.uniform(38.0, 78.0)
            offset = pygame.Vector2(math.cos(angle), math.sin(angle)) * distance
            self.particles.append(Particle(position.copy(), position + offset, color))

    def _collect(self, drop: Drop) -> None:
        self.combo += 1
        multiplier = 1 + min(4, self.combo // 5)
        self.score += 100 * multiplier
        self.score_bump_age = 0.0
        self._burst(drop.position, drop.color)

    def _hit(self, drop: Drop) -> None:
        self.shields -= 1
        self.combo = 0
        self.hit_flash_age = 0.0
        self._burst(drop.position, RED)
        if self.shields <= 0:
            self.game_over = True

    def _pulse_radius(self) -> float:
        if self.pulse_age is None:
            return 0.0
        return interpolate(0.0, 190.0, min(1.0, self.pulse_age / 0.55), "quint_out")

    def update(self, dt: float) -> None:
        if self.paused:
            return
        if self.game_over:
            self.finished_age += dt
            return

        self.elapsed += dt
        self.player.update(dt)
        self.spawn_in -= dt
        self.score_bump_age += dt
        self.hit_flash_age += dt

        if self.spawn_in <= 0.0:
            self._spawn_drop()

        if self.pulses < 3:
            self.recharge_age += dt
            if self.recharge_age >= 10.0:
                self.pulses += 1
                self.recharge_age -= 10.0
        else:
            self.recharge_age = 0.0

        if self.pulse_age is not None:
            self.pulse_age += dt
            if self.pulse_age >= 0.55:
                self.pulse_age = None

        player_position = self.player.position
        survivors = []
        pulse_radius = self._pulse_radius()
        for drop in self.drops:
            drop.age += dt
            distance = drop.position.distance_to(player_position)
            if drop.kind == "hazard" and pulse_radius > 0.0 and distance <= pulse_radius:
                self.score += 50
                self._burst(drop.position, CYAN)
            elif distance <= 31.0:
                self._collect(drop) if drop.kind == "core" else self._hit(drop)
            elif drop.progress < 1.0:
                survivors.append(drop)
            elif drop.kind == "core":
                self.combo = 0
        self.drops = survivors

        for particle in self.particles:
            particle.age += dt
        self.particles = [particle for particle in self.particles if particle.alive]

        if self.elapsed >= RUN_SECONDS:
            self.game_over = True

    def _draw_background(self) -> None:
        self.screen.fill((7, 10, 25))
        glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for x, y, radius, offset in self.stars:
            phase = ping_pong(self.elapsed + offset, leg_seconds=1.4)
            brightness = int(interpolate(55, 185, phase, "sine_in_out"))
            pygame.draw.circle(glow, (115, 155, 255, brightness), (x, y), radius)
        self.screen.blit(glow, (0, 0))

        pygame.draw.rect(self.screen, (12, 18, 42), PLAY_RECT, border_radius=18)
        pygame.draw.rect(self.screen, (41, 58, 105), PLAY_RECT, width=2, border_radius=18)
        for index in range(1, LANE_COUNT):
            x = PLAY_RECT.left + index * PLAY_RECT.width / LANE_COUNT
            pygame.draw.line(
                self.screen,
                (28, 40, 75),
                (x, PLAY_RECT.top + 16),
                (x, PLAY_RECT.bottom - 16),
                width=1,
            )

    def _draw_drop(self, drop: Drop) -> None:
        position = drop.position
        scale = max(0.2, drop.scale)
        size = max(6, round(17 * scale))
        halo_phase = ping_pong(self.elapsed + drop.lane * 0.17, leg_seconds=0.6)
        halo = round(interpolate(size + 4, size + 11, halo_phase, "sine_in_out"))

        if drop.kind == "core":
            pygame.draw.circle(
                self.screen, _mix(drop.color, (255, 255, 255), 0.2), position, halo, 2
            )
            pygame.draw.circle(self.screen, drop.color, position, size)
            pygame.draw.circle(self.screen, (245, 251, 255), position, max(3, size // 3))
        else:
            points = [
                (position.x, position.y - size),
                (position.x + size, position.y),
                (position.x, position.y + size),
                (position.x - size, position.y),
            ]
            pygame.draw.polygon(self.screen, (73, 17, 38), points)
            pygame.draw.polygon(self.screen, RED, points, width=3)
            pygame.draw.line(
                self.screen,
                RED,
                (position.x - size // 3, position.y - size // 3),
                (position.x + size // 3, position.y + size // 3),
                width=3,
            )

        label = f"{drop.label}{' GLITCH' if drop.kind == 'hazard' else ''}"
        text_image = self.small_font.render(label, True, drop.color)
        text_rect = text_image.get_rect(midbottom=(position.x, position.y - halo - 5))
        self.screen.blit(text_image, text_rect)

    def _draw_player(self) -> None:
        position = self.player.position
        flame_phase = ping_pong(self.elapsed, leg_seconds=0.22)
        flame = interpolate(13.0, 25.0, flame_phase, "sine_in_out")
        pygame.draw.polygon(
            self.screen,
            GOLD,
            [
                (position.x - 8, position.y + 13),
                (position.x, position.y + flame),
                (position.x + 8, position.y + 13),
            ],
        )
        pygame.draw.polygon(
            self.screen,
            CYAN,
            [
                (position.x, position.y - 24),
                (position.x + 25, position.y + 18),
                (position.x, position.y + 10),
                (position.x - 25, position.y + 18),
            ],
        )
        pygame.draw.circle(self.screen, (235, 250, 255), (position.x, position.y - 3), 7)

        if self.pulse_age is not None:
            radius = round(self._pulse_radius())
            alpha = round(interpolate(210.0, 0.0, self.pulse_age / 0.55, "cubic_in"))
            pulse_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.circle(pulse_surface, (*CYAN, alpha), position, radius, width=4)
            self.screen.blit(pulse_surface, (0, 0))

    def _draw_particles(self) -> None:
        layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for particle in self.particles:
            progress = particle.age / particle.duration
            position = interpolate(particle.start, particle.end, progress, "cubic_out")
            radius = max(1, round(interpolate(5.0, 0.0, progress, "cubic_in")))
            alpha = round(interpolate(230.0, 0.0, progress, "cubic_in"))
            pygame.draw.circle(layer, (*particle.color, alpha), position, radius)
        self.screen.blit(layer, (0, 0))

    def _draw_hud(self) -> None:
        _draw_text(self.screen, self.title_font, "EASING GAUNTLET", INK, (38, 28))
        _draw_text(
            self.screen,
            self.body_font,
            "Catch motion cores. Dodge red glitches.",
            MUTED,
            (40, 79),
        )

        sidebar = pygame.Rect(824, 112, 238, 570)
        pygame.draw.rect(self.screen, (12, 18, 42), sidebar, border_radius=18)
        pygame.draw.rect(self.screen, (41, 58, 105), sidebar, width=2, border_radius=18)

        _draw_text(self.screen, self.small_font, "SCORE", MUTED, (848, 140))
        score_image = self.heading_font.render(f"{self.score:06d}", True, INK)
        if self.score_bump_age < 0.32:
            if self.score_bump_age < 0.12:
                scale = interpolate(1.0, 1.24, self.score_bump_age / 0.12, "back_out")
            else:
                scale = interpolate(1.24, 1.0, (self.score_bump_age - 0.12) / 0.2, "sine_out")
            score_image = pygame.transform.smoothscale_by(score_image, scale)
        self.screen.blit(score_image, score_image.get_rect(topleft=(848, 164)))

        remaining = max(0.0, RUN_SECONDS - self.elapsed)
        _draw_text(self.screen, self.small_font, "TIME", MUTED, (848, 214))
        _draw_text(self.screen, self.heading_font, f"{remaining:04.1f}s", GOLD, (848, 237))
        _draw_text(self.screen, self.small_font, f"COMBO  x{self.combo}", GREEN, (848, 283))

        _draw_text(self.screen, self.small_font, "SHIELDS", MUTED, (848, 322))
        for index in range(3):
            color = CYAN if index < self.shields else (48, 58, 82)
            pygame.draw.rect(
                self.screen,
                color,
                pygame.Rect(848 + index * 54, 347, 40, 10),
                border_radius=5,
            )

        _draw_text(self.screen, self.small_font, "SPACE PULSES", MUTED, (848, 386))
        for index in range(3):
            color = VIOLET if index < self.pulses else (48, 58, 82)
            pygame.draw.circle(self.screen, color, (860 + index * 38, 421), 10, width=3)

        _draw_text(self.screen, self.small_font, "EASING IN PLAY", MUTED, (848, 461))
        easing_lines = (
            ("Cubic Out", "lane change", CYAN),
            ("Elastic Out", "spawn pop", GREEN),
            ("Sine In-Out", "halos + stars", BLUE),
            ("Quint Out", "safety pulse", VIOLET),
            ("Back Out", "score feedback", PINK),
        )
        for index, (name, purpose, color) in enumerate(easing_lines):
            y = 490 + index * 31
            pygame.draw.circle(self.screen, color, (854, y + 7), 4)
            _draw_text(self.screen, self.small_font, name, INK, (866, y - 2))
            _draw_text(self.screen, self.small_font, purpose, MUTED, (952, y - 2))

        _draw_text(
            self.screen,
            self.small_font,
            "A / D or arrows   SPACE pulse   P pause   R restart",
            MUTED,
            (40, 692),
        )

    def _draw_overlay(self) -> None:
        if self.hit_flash_age < 0.22:
            alpha = round(interpolate(115.0, 0.0, self.hit_flash_age / 0.22, "sine_out"))
            flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash.fill((*RED, alpha))
            self.screen.blit(flash, (0, 0))

        if self.paused:
            veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            veil.fill((4, 7, 19, 190))
            self.screen.blit(veil, (0, 0))
            _draw_text(
                self.screen,
                self.title_font,
                "PAUSED",
                INK,
                (WIDTH / 2, HEIGHT / 2 - 12),
                center=True,
            )
            _draw_text(
                self.screen,
                self.body_font,
                "Press P to return to the curve run",
                MUTED,
                (WIDTH / 2, HEIGHT / 2 + 36),
                center=True,
            )

        if self.game_over:
            progress = min(1.0, self.finished_age / 0.55)
            veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            veil.fill((4, 7, 19, round(interpolate(0.0, 215.0, progress, "sine_out"))))
            self.screen.blit(veil, (0, 0))
            panel_y = interpolate(HEIGHT + 120.0, 210.0, progress, "back_out")
            panel = pygame.Rect(290, round(panel_y), 520, 250)
            pygame.draw.rect(self.screen, (18, 27, 58), panel, border_radius=22)
            pygame.draw.rect(self.screen, VIOLET, panel, width=3, border_radius=22)
            heading = "RUN COMPLETE" if self.elapsed >= RUN_SECONDS else "SIGNAL LOST"
            _draw_text(
                self.screen,
                self.heading_font,
                heading,
                INK,
                (WIDTH / 2, panel.y + 55),
                center=True,
            )
            _draw_text(
                self.screen,
                self.title_font,
                f"{self.score:06d}",
                GOLD,
                (WIDTH / 2, panel.y + 120),
                center=True,
            )
            _draw_text(
                self.screen,
                self.body_font,
                "Press R or Enter to run the gauntlet again",
                MUTED,
                (WIDTH / 2, panel.y + 192),
                center=True,
            )

    def draw(self) -> None:
        self._draw_background()
        previous_clip = self.screen.get_clip()
        self.screen.set_clip(PLAY_RECT)
        for drop in self.drops:
            self._draw_drop(drop)
        self._draw_particles()
        self._draw_player()
        self.screen.set_clip(previous_clip)
        self._draw_hud()
        self._draw_overlay()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7, help="random seed for a repeatable run")
    parser.add_argument(
        "--frames",
        type=int,
        help="render a fixed number of 60 FPS frames and exit (useful for smoke tests)",
    )
    parser.add_argument("--screenshot", type=Path, help="save the final rendered frame as PNG")
    args = parser.parse_args()
    if args.frames is not None and args.frames <= 0:
        parser.error("--frames must be greater than zero")
    return args


def main() -> None:
    args = _parse_args()
    pygame.init()
    pygame.display.set_caption("Easing Gauntlet - Easing Lab playable example")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    pygame.key.set_repeat(170, 90)
    game = EasingGauntlet(screen, seed=args.seed)
    running = True
    frame = 0

    try:
        while running:
            dt = 1.0 / FPS if args.frames is not None else min(0.05, clock.tick(FPS) / 1000.0)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        game.move_player(-1)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        game.move_player(1)
                    elif event.key == pygame.K_SPACE:
                        game.activate_pulse()
                    elif event.key == pygame.K_p:
                        game.toggle_pause()
                    elif event.key == pygame.K_r or event.key == pygame.K_RETURN and game.game_over:
                        game.reset()

            if args.frames is not None:
                if frame % 95 == 20:
                    game.move_player(1 if (frame // 95) % 2 == 0 else -1)
                if frame == 165:
                    game.activate_pulse()

            game.update(dt)
            game.draw()
            pygame.display.flip()
            frame += 1
            if args.frames is not None and frame >= args.frames:
                running = False

        if args.screenshot is not None:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(screen, args.screenshot)
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
