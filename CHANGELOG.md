# Changelog

All notable changes to Easing Lab are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## 0.3.0 - 2026-08-21

### Added

- Expo In, Out, and In-Out library functions and easings.net-style aliases.
- A five-stage Steps easing with `step` and `stepped` resolver aliases.

### Changed

- Consolidated the designer's similar Sine / Cosine, Smoothstep, and Smootherstep cards
  under the clearer Smoothstep name.
- Replaced the two freed designer slots with visibly distinct Expo Out and Steps cards.
- Refreshed the designer preview media for the new nine-curve set.
- Bumped the package version to 0.3.0.

### Compatibility

- Sine, Smoothstep, and Smootherstep library functions, registry keys, aliases, and legacy
  closed-form documents remain supported.

## 0.2.0 - 2026-08-17

### Added

- Easing Gauntlet, a playable Pygame example with eased lane changes, falling motion,
  spawn effects, safety pulses, score feedback, particles, and background animation.
- A deterministic headless smoke test for the playable example.
- A six-second gameplay animation in the README, rendered directly from Easing Gauntlet.

### Fixed

- The game-feel drawer now follows the selected easing, matching its companion motion
  indicator and reflecting live curve edits.

## 0.1.0 - 2026-08-17

### Added

- Side-effect-free easing library with 21 built-in keys and nine designer presets.
- In and Out variants for the Sine, Cubic, Quint, Back, Bounce, and Elastic families,
  including easings.net-style import and resolver aliases.
- Scalar and `pygame.Vector2` interpolation helper.
- Validated, callable Hermite curves with versioned JSON loading.
- Resizable Pygame designer with curve editing, import, export, and screenshot modes.
- Deterministic, color-preserving README GIF renderer and an 8.4-second app animation.
- Cross-platform CI, unit tests, a headless application smoke test, and build verification.
- A core-only CI job that installs the package without extras and tests the math library
  without Pygame.
- A verification record for exact test conditions, media checks, and provenance.

### Changed

- Pygame is optional under the `app` extra; the base install contains only the
  side-effect-free math library.
- The README leads with installation and runnable examples for library and designer users.
- Exported curve JSON is explicitly unrestricted for commercial and closed-source use.

### Fixed

- Two-point Linear curves now use their chord slope and remain exactly linear.
- Launching the designer without Pygame prints the required install command instead of
  exposing a `ModuleNotFoundError` traceback.
