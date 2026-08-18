# Changelog

All notable changes to Easing Lab are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Deterministic, color-preserving README GIF renderer and a current 8.4-second app animation.
- In and Out variants for the Sine, Cubic, Quint, Back, Bounce, and Elastic families,
  including easings.net-style import and resolver aliases.
- A core-only CI job that installs the package without extras and tests the math library
  without Pygame.
- A verification record for exact test conditions, media checks, and provenance.

### Changed

- Pygame is now optional under the `app` extra; the base install contains only the
  side-effect-free math library.
- The README now leads with installation and runnable examples for library and designer
  users.

### Fixed

- Launching the designer without Pygame now prints the required install command instead of
  exposing a `ModuleNotFoundError` traceback.

## 0.1.0 - 2026-08-17

### Added

- Side-effect-free easing library with nine presets and aliases.
- Scalar and `pygame.Vector2` interpolation helper.
- Validated, callable Hermite curves with versioned JSON loading.
- Resizable Pygame designer with curve editing, import, export, and screenshot modes.
- Cross-platform CI, unit tests, a headless application smoke test, and build verification.

### Fixed

- Two-point Linear curves now use their chord slope and remain exactly linear.
