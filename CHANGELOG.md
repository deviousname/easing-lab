# Changelog

All notable changes to Easing Lab are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## 0.1.0 - 2026-08-17

### Added

- Side-effect-free easing library with nine presets and aliases.
- Scalar and `pygame.Vector2` interpolation helper.
- Validated, callable Hermite curves with versioned JSON loading.
- Resizable Pygame designer with curve editing, import, export, and screenshot modes.
- Cross-platform CI, unit tests, a headless application smoke test, and build verification.

### Fixed

- Two-point Linear curves now use their chord slope and remain exactly linear.
