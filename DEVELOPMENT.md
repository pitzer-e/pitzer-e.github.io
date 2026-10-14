# Reproducible development environment

Development uses Python **3.13.16**, uv **0.13.0**, and Quarto CLI
**1.10.19** on macOS ARM64 and Linux x86-64. PR validation uses Ubuntu
24.04 only. Production retains its independent requirements and workflow.

Install uv 0.13.0 using your preferred isolated tool installer (for example,
`pipx install uv==0.13.0`). Install the matching Quarto CLI release from
<https://github.com/quarto-dev/quarto-cli/releases/tag/v1.10.19> and put its
`bin` directory on PATH. The Python `quarto` dependency is a separate package;
it does not install or pin the Quarto CLI.

From the repository root:

```sh
uv --version                    # uv 0.13.0
quarto --version                # 1.10.19
uv python install 3.13.16
uv sync --locked
uv run --locked python --version
uv run --locked python scripts/validate_dev.py
```

The project is not packaged. `.python-version` selects the interpreter;
`pyproject.toml` limits development to Python 3.13 and enforces the exact uv
version. `uv.lock` records dependency versions, distribution hashes, and
platform markers. All 15 original dependency declarations are retained;
constraints preserve their versions from the pre-milestone local environment
rather than upgrading the numerical stack. Existing transitive versions are also retained through constraints and locked.
Use `--locked` so configuration drift fails instead of silently changing the lock.

For a fresh environment, move any existing `.venv` out of the way before
`uv sync --locked`. During Milestone 002 the previous local environment was
preserved as `.venv.pre-milestone-002`; both paths are ignored. Each developer
must install the pinned interpreter locally; virtual environments are not portable.

The validation command checks exact Python and Quarto versions, runs the existing
73 tests, validates the saved FQHC snapshot, and renders the whole website in a
temporary copy of tracked files. It checks saved-data hashes after rendering and
all tracked checkout hashes before returning. Generated output is discarded.
It does not fetch source data or rebuild the snapshot. Newly added site source
files must be tracked before this command includes them in its temporary copy.

To run only the existing quality gates:

```sh
uv run --locked python -m pytest -p no:cacheprovider projects/oregon-fqhc/tests/
uv run --locked python projects/oregon-fqhc/scripts/4_analyze_correlations.py
```

The PR workflow has read-only repository permissions, does not retain Git
credentials, and runs only on Linux pull requests. It installs the pinned tools
and locked environment and uses the same isolated validation command. It neither
publishes output nor invokes the production pipeline. Linux execution must still
be confirmed by an approved PR run; local macOS validation is not Linux evidence.

Dependency changes require a separate compatibility review and rerunning these
gates. Do not loosen numerical tolerances to accommodate a failing environment.
Keep `requirements.txt` and `.github/workflows/daily_update.yml` independent until
a production migration is explicitly approved.
