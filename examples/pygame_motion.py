"""Minimal Easing Lab integration in a Pygame loop."""

import pygame

from easing_lab import interpolate, ping_pong


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((800, 480))
    pygame.display.set_caption("Easing Lab example")
    clock = pygame.time.Clock()
    start = pygame.Vector2(80, screen.get_height() / 2)
    end = pygame.Vector2(screen.get_width() - 80, screen.get_height() / 2)
    elapsed = 0.0
    running = True

    try:
        while running:
            elapsed += clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if (
                    event.type == pygame.QUIT
                    or event.type == pygame.KEYDOWN
                    and event.key == pygame.K_ESCAPE
                ):
                    running = False

            t = ping_pong(elapsed, leg_seconds=1.2)
            position = interpolate(start, end, t, "back")

            screen.fill("#12141a")
            pygame.draw.line(screen, "#434a5c", start, end, width=3)
            pygame.draw.circle(screen, "#67d2ff", position, 14)
            pygame.display.flip()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
