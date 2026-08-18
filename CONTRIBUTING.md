# Contributing to Easing Lab

Thanks for helping make easing easier to see, feel, and reuse.

## Before opening an issue

- Search existing issues first.
- Include your operating system, Python version, Pygame version, and the exact command used.
- For designer problems, attach a screenshot or exported curve JSON when it helps reproduce
  the behavior.
- Never include secrets, private paths, or personal data in logs or screenshots.

Bug reports and focused usability suggestions are welcome. Large feature proposals should
start as an issue so the interaction and file-format impact can be discussed before code is
written.

## Local setup

```bash
git clone https://github.com/deviousname/easing-lab.git
cd easing-lab
python -m venv .venv
python -m pip install -e ".[dev]"
```

Activate the virtual environment using the command appropriate for your shell, then run:

```bash
ruff format --check .
ruff check .
pytest
python -m build
```

## Pull requests

- Keep one concern per pull request.
- Add or update tests for changed behavior.
- Preserve side-effect-free imports for the public library.
- Preserve JSON version checks and control-point validation.
- Do not add media or code unless its provenance and license are clear.
- Explain what changed, why, how it was tested, and what was not tested.

By contributing, you agree that your contribution is licensed under this repository's MIT
License.
