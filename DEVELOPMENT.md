# Reproducible development environment

Development uses Python **3.13.16**, uv **0.13.0**, and Quarto CLI
**1.10.19**. PR validation uses Ubuntu 24.04 x86-64, macOS 15 ARM64, and
Windows Server 2025 x64. Production retains its independent requirements and workflow.

Platform verification status:

- Linux x86-64 (`ubuntu-24.04`): Complete hosted validation passed.
- macOS ARM64 (`macos-15`): Complete hosted validation passed; fresh local
  environment also validated.
- Windows x64 (`windows-2025`): Complete hosted validation passed.

All three hosted platforms passed 73 tests, saved-snapshot validation, full
isolated rendering, output assertions, and copied-data/original-checkout integrity
checks. Output assertions verify exactly ten HTML pages, engineering documentation
exclusion from output and search metadata, navigation and case-study links, and
the linked FQHC data contract matching its source bytes.

This evidence applies to the listed runner OS/architecture combinations with the
pinned tools and lockfile. Other OS versions and hardware architectures have not
been validated.

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
temporary copy of tracked files outside the checkout. It captures copied-data
hashes before tests and checks them after validation, including on failure.
Original tracked checkout hashes are captured before platform/tool verification and
checked on every exit, including early verification failures. If validation and
integrity both fail, the original exception is retained and the integrity violation
is reported as an additional error. Generated output is discarded.

The website explicitly renders only `**/*.qmd`: its ten intended pages.
Developer and engineering Markdown are not render targets. The README and FQHC
data-contract Markdown remain repository documentation, not additional website pages.
It does not fetch source data or rebuild the snapshot. Newly added site source
files must be tracked before this command includes them in its temporary copy.

To run only the existing quality gates:

```sh
uv run --locked python -m pytest -p no:cacheprovider projects/oregon-fqhc/tests/
uv run --locked python projects/oregon-fqhc/scripts/4_analyze_correlations.py
```

The PR workflow has read-only repository permissions, does not retain Git
credentials, and runs the same complete validation on three independent platform
jobs for pull requests targeting main. Matrix failures do not cancel other jobs. It installs the pinned tools
and locked environment in separate steps so installation failures cannot be
hidden by a later successful native command on Windows. It uses the same isolated validation command. It neither
publishes output nor invokes the production pipeline. All three hosted matrix
jobs passed independently of the fresh local macOS validation.

CI verifies runner OS/architecture and the 64-bit interpreter architecture. It
uses uv-managed Python 3.13.16, verifies Quarto 1.10.19, and passes the exact
project interpreter path to Quarto. Git newline conversion is disabled before
checkout to preserve saved artifact fingerprints on Windows. Python subprocesses
use `sys.executable`, avoiding platform-specific virtual-environment paths.
Existing freeze settings remain: FQHC executes fresh; other reports may use
frozen outputs. Full-site rendering does not mean every report executes fresh.

Dependency changes require a separate compatibility review and rerunning these
gates. Do not loosen numerical tolerances to accommodate a failing environment.
Keep `requirements.txt` and `.github/workflows/daily_update.yml` independent until
a production migration is explicitly approved.
