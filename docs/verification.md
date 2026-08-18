# Easing Lab verification record

This document keeps the engineering evidence behind the public README.

> **Observed** means exercised in this repository under the stated conditions.
> **Derived** means based on a linked public source or standard mathematics.
> **Inferred** means expected but not yet verified in that environment.

## Dependency boundary

- **Observed:** `src/easing_lab/core.py` imports only the Python standard library. Its one
  mention of `pygame.Vector2` describes the interpolation protocol; it is not an import.
- **Derived:** the base project metadata has no runtime dependencies. Pygame is gated behind
  the `app` extra, while the `dev` extra includes the app dependencies for the full suite and
  GIF renderer.
- **Observed:** `tests/test_package.py` skips its designer checks when Pygame is unavailable,
  while `tests/test_core.py` remains runnable.
- **Observed:** CI has a separate core-only job that installs the package without extras,
  asserts that Pygame is absent, imports `easing_lab`, and runs `tests/test_core.py`.

## Library and designer behavior

- **Observed:** importing `easing_lab` does not open a window or initialize Pygame display,
  font, or audio state.
- **Observed:** the standalone designer is resizable and provides nine curated starting
  curves. Eight can be edited and the exact Sine / Cosine projection remains locked.
- **Observed:** control points can be edited, reset, imported, and exported as versioned
  JSON.
- **Derived:** the locked Sine / Cosine curve is the normalized one-dimensional projection
  of circular motion: `(1 - cos(pi*t)) / 2`.
- **Observed:** the public registry contains 21 built-in keys: Linear, Smoothstep,
  Smootherstep, and In, Out, and In-Out variants for six easing families.
- **Observed:** endpoint tests cover every built-in key. Reflection tests independently
  enforce `out(t) == 1 - in(1 - t)` for Sine, Cubic, Quint, Back, Bounce, and Elastic.
- **Observed:** the representative-value test uses hand-derived literals independent of
  implementation constants and code paths.

## Design corrections retained from the proof of concept

- **Observed:** the proof of concept initialized Pygame and entered its event loop during
  import. The package moves lifecycle work into `EasingLabApp` and guarantees cleanup with
  `pygame.quit()`.
- **Observed:** the original two-point Linear preset used zero Hermite endpoint slopes and
  therefore evaluated as Smoothstep. Two-point curves now use their chord slope; a
  regression test fixes the expected quarter-point value at `0.25`.
- **Observed:** three-or-more-point custom curves retain zero endpoint slopes and centered
  internal slopes, preserving the editor's arrive-at-rest and leave-at-rest behavior.
- **Derived:** Pygame's public guidance recommends `pygame.quit()` on exit; the app owns that
  cleanup explicitly. See the [Pygame FAQ](https://www.pygame.org/wiki/FrequentlyAskedQuestions).

## README media

- **Observed:** `tools/render_readme_gif.py` renders the current app deterministically rather
  than recording borrowed media.
- **Observed:** `docs/easing-lab.gif` is a 1200×800, 168-frame animation at 20 frames per
  second. Its 8.4-second cycle has no duplicate endpoint and uses a fixed 128-color palette.
- **Observed:** the renderer verifies the loop boundary, timing metadata, frame count, and
  every optimized frame after decoding. The checked artifact is 2,653,868 bytes.
- **Observed:** the PNG preview and animated GIF contain only graphics rendered by Easing Lab
  itself; the repository contains no downloaded font, sound, art, or other media asset.

## Provenance and credits

- **Observed:** the easing implementation comes from the user-owned proof of concept and was
  reorganized into an original package without proprietary SDKs or decompiled sources.
- **Derived:** the Back, Bounce, and Elastic families descend from
  [Robert Penner's easing equations](https://robertpenner.com/easing/). Attribution is
  customary in animation libraries and is recorded in the relevant docstrings and README.
- **Derived:** family names and comparison terminology follow the public catalog at
  [easings.net](https://easings.net/).
- **Derived:** Pygame is a separate LGPL-licensed optional dependency. Its package metadata
  and license are available on [PyPI](https://pypi.org/project/pygame/).
- **Observed:** Easing Lab's own source is licensed under the repository's MIT `LICENSE`.

## Compatibility and release checks

- **Observed:** CI covers Windows and Ubuntu on Python 3.10 and 3.13. The core-only job uses
  Python 3.13 on Ubuntu.
- **Inferred:** other SDL-supported desktop environments may work, but are not claimed until
  exercised by CI or a reported live test.
- **Observed (2026-08-17 19:26 PDT):** PyPI's official JSON and Simple endpoints for
  `pygame-easing-lab` both returned HTTP 404, and `pip index versions pygame-easing-lab`
  reported `No matching distribution found`. The human project URL returned PyPI's generic
  `Client Challenge` page and provided no additional project evidence. No published project
  or release using that normalized name was visible at that moment; this is a registry check,
  not a reservation.
- **Derived:** [PyPI's project-name guidance](https://pypi.org/help/#project-name) says a
  name can still be rejected when it is too similar to another project, prohibited, or
  registered without a release. No registration or upload was attempted, so final acceptance
  remains a publishing-time check.

## RC2 local verification

All checks in this section ran on Windows 11 build 26200 with CPython 3.13.14.

### Base install without extras

- **Observed:** `python -m pip install .` built and installed `pygame-easing-lab==0.1.0`
  in a new virtual environment. Before the test runner was added, `pip list --format=freeze`
  contained only `pip==26.1.2` and `pygame-easing-lab==0.1.0`.
- **Observed:** `import easing_lab` succeeded and `importlib.util.find_spec("pygame")`
  returned `None`.
- **Observed:** after installing pytest separately, the final isolated command
  `python -m pytest tests/test_core.py -q` reported `104 passed in 0.06s`.
- **Observed:** the first core-test invocation inherited the repository's configured
  `.pytest-tmp` path and ended with 92 passes plus one Windows permission error while
  removing that shared directory. Re-running with fresh temporary and cache directories
  under the clean environment produced the 104-pass result above.
- **Observed:** running the installed console command without Pygame exited with status 1
  and printed exactly:

  ```text
  The Easing Lab designer needs Pygame. Install it with:
    pip install "pygame-easing-lab[app]"
  ```

### App install

- **Observed:** `python -m pip install ".[app]"` in a second new virtual environment
  installed `pygame-easing-lab==0.1.0` and `pygame==2.6.1`.
- **Observed:** with `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy`, the installed
  `easing-lab` command rendered a 71,071-byte PNG at 1180×760 and exited successfully. The
  file had the PNG signature and exceeded the smoke test's 10,000-byte floor.

### Full project and distributions

- **Observed:** `ruff format --check .` reported 13 files already formatted.
- **Observed:** `ruff check .` reported all checks passed.
- **Observed:** the final full suite reported `106 passed in 0.45s`.
- **Observed:** two preliminary final-suite commands did not complete: one crossed Windows
  ownership contexts and hit the same `.pytest-tmp` permission conflict; the next supplied
  an absolute temporary path without first creating its parent. Neither reported a failed
  product assertion. Creating the parent and keeping both pytest paths isolated produced the
  106-pass result above.
- **Observed:** `python -m build` produced both
  `pygame_easing_lab-0.1.0.tar.gz` and
  `pygame_easing_lab-0.1.0-py3-none-any.whl`.
- **Observed:** wheel metadata contains no unconditional `Requires-Dist`. The `app` extra
  requires `pygame>=2.6.1,<3`; the `dev` extra includes that same requirement plus Build,
  Pillow, pytest, and Ruff.
- **Observed:** the wheel contains only the runtime package and distribution metadata. The
  source archive includes the README media, GIF renderer, and this verification record.
