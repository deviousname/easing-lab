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
- **Observed (2026-08-17 19:40 PDT):** PyPI's official JSON and Simple endpoints for
  `easing-lab` both returned HTTP 404, and `pip index versions easing-lab` exited with status
  1 after reporting `No matching distribution found`. No published project or release using
  that normalized name was visible at that moment; this is a registry check, not a
  reservation.
- **Derived:** [PyPI's project-name guidance](https://pypi.org/help/#project-name) says a
  name can still be rejected when it is too similar to another project, prohibited, or
  registered without a release. No registration or upload was attempted, so final acceptance
  remains a publishing-time check.

## 0.1.0 local release verification

All checks in this section ran on Windows 11 build 26200 with CPython 3.13.14.

### Base install without extras

- **Observed:** `python -m pip install .` built and installed `easing-lab==0.1.0` in a new
  virtual environment. Before the test runner was added, `pip list --format=freeze`
  contained only `easing-lab==0.1.0` and `pip==26.1.2`.
- **Observed:** `import easing_lab` succeeded and `importlib.util.find_spec("pygame")`
  returned `None`; `easing_lab.__version__` was `0.1.0`.
- **Observed:** after installing pytest separately, the final isolated command
  `python -m pytest tests/test_core.py -q` reported `104 passed in 0.07s`.
- **Observed:** the first fresh-environment harness stopped after the successful base install
  and package list because PowerShell passed a stray backslash to an inline Python command,
  causing a `SyntaxError`. A new pair of virtual environments with corrected quoting produced
  every result in this section.
- **Observed:** running the installed console command without Pygame exited with status 1
  and printed exactly:

  ```text
  The Easing Lab designer needs Pygame. Install it with:
    pip install "easing-lab[app]"
  ```

### App install

- **Observed:** `python -m pip install ".[app]"` in a second new virtual environment
  installed `easing-lab==0.1.0` and `pygame==2.6.1`.
- **Observed:** with `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy`, the installed
  `easing-lab` command rendered a 71,071-byte PNG at 1180×760 and exited successfully. The
  file had the PNG signature and exceeded the smoke test's 10,000-byte floor.

### Full project and distributions

- **Observed:** `ruff format --check .` reported 13 files already formatted.
- **Observed:** `ruff check .` reported all checks passed.
- **Observed:** the final full suite reported `106 passed in 0.49s`.
- **Observed:** `python -m build` produced both
  `easing_lab-0.1.0.tar.gz` and `easing_lab-0.1.0-py3-none-any.whl`. In the verification
  build made immediately before this record was refreshed, they were 30,092 bytes and
  20,406 bytes respectively.
- **Observed:** the first renamed build resolved Hatchling 1.32.0, emitted core metadata 2.5,
  and then failed `twine check` with `Invalid distribution metadata: '2.5' is not a valid
  metadata version`. Bounding the isolated build backend to `hatchling>=1.27,<1.30` restored
  metadata 2.4; both artifacts then passed `twine check`.
- **Observed:** wheel metadata contains no unconditional `Requires-Dist`. The `app` extra
  requires `pygame>=2.6.1,<3`; the `dev` extra includes that same requirement plus Build,
  Pillow, pytest, and Ruff.
- **Observed:** the wheel contains only the runtime package and distribution metadata. The
  source archive excludes the 2.65 MB README GIF and PNG, `.github`, and `.pytest-tmp`; it
  retains the GIF renderer and this verification record.

### TestPyPI rehearsal

- **Observed (2026-08-17):** TestPyPI accepted both 0.1.0 artifacts. Its JSON API reported
  the 20,402-byte wheel with SHA-256
  `b5d62bde131cc15e4e768aba79700ff8ff6e03ab9281e1c904b71e9e46da20ad` and the
  30,124-byte source archive with SHA-256
  `14d9581eb699f7ff6be746c34487994f9c407de6c83c784bc717bcea0bba1252`.
- **Observed:** downloading the wheel back from TestPyPI reproduced its recorded size and
  SHA-256. A new CPython 3.13 environment installed it with `--no-deps`; both the
  distribution and import reported version `0.1.0`, `pygame` remained absent, and the
  package list contained only `easing-lab==0.1.0` and `pip==26.1.2`.
- **Observed:** the TestPyPI page rendered the description, install command, MIT license,
  project URLs, classifiers, and both download files. Its audit also found that repository-
  relative README media and document links were rewritten as nonexistent TestPyPI URLs.
  Those links were changed to absolute GitHub URLs before preparing the real-PyPI candidate.
- **Observed:** the CI badge cannot load from TestPyPI while the GitHub repository is
  private. Its URL is already absolute and will become readable when the repository is made
  public.
- **Observed:** the TestPyPI 0.1.0 files predate the README-link correction and cannot be
  replaced. The real-PyPI candidate is rebuilt and rechecked after that correction, so its
  hashes are intentionally different; package code and dependency metadata are unchanged.
