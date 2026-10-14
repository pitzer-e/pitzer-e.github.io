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

## Production environment migration

The proposed production workflow uses Ubuntu 24.04 x86-64, uv 0.13.0,
uv-managed Python 3.13.16, and Quarto CLI 1.10.19. It synchronizes with
`uv sync --locked`, runs Python through `uv run --locked`, and explicitly passes
the project interpreter to Quarto. Production retains the Monday 14:00 UTC
schedule, manual dispatch, authenticated checkout, `contents: write`, and the
existing publishing allowlist. A production-specific concurrency group prevents
overlapping runs; an active run is not cancelled. GitHub may replace an older
pending run with a newer pending run, so this is not a queue guaranteeing every
request executes.

Before activation, rehearse on disposable Ubuntu 24.04 x86-64 infrastructure:

1. Copy the tracked repository and saved workbooks outside the original checkout.
   Record original hashes. Provide no publishing credentials or usable remote.
2. Install the pinned tools and synchronize the unchanged lock. Verify interpreter
   and runner architecture and explicitly select that interpreter for Quarto.
3. Run the 73 tests and saved-artifact validator against the copied baseline.
4. Run `uv run --locked python projects/oregon-fqhc/scripts/run_pipeline.py --local`
   only in the copy. This rebuilds from saved workbooks without HRSA downloads.
5. Rerun the tests and saved-artifact validator. Render the complete site using
   `uv run --locked quarto render` and apply `verify_website()` to the output.
6. Compare generated CSVs and summary against the saved baseline using exact
   identifiers, counts, non-model values, and the existing model tolerances.
7. Inspect the production allowlist in a disposable Git index without committing
   or pushing. Verify all original files, the checkpoint, and prior environment
   remain unchanged. Review the rendered website in a browser.

The completed macOS ARM64 saved-input rehearsal produced byte-identical CSVs.
Fourteen model values differed within existing tolerances (relative 1e-13,
absolute 1e-15). Local-build timestamps, source age, summary fingerprints, and
`local_snapshot` provenance differ intentionally. Local mode does not represent
a new retrieval. Plotly runtime, generated chart IDs, CSS fingerprints, dates,
and listing metadata may differ; structural checks do not replace browser review.
No tolerances or analytical behavior are changed by this migration.

The completed saved-input activation gates require a passing Linux x86-64 rebuild
rehearsal, all 73 tests,
saved-artifact validation, exactly ten rendered pages, engineering-document
exclusion from output/search, intact navigation/listings and the linked FQHC data
contract, unchanged protected inputs/sources, allowlisted publishing differences,
and browser review of interactive plots. Live downloads and actual publishing
require separate authorization. Linux rebuild and limited browser evidence are recorded below. The presentation
caveat and untested live/publishing/deployment paths remain operational review items.

Repository publication and website deployment are distinct. This workflow commits
and pushes allowlisted generated artifacts. Pages serves `main:/docs`; a push using
`GITHUB_TOKEN` does not itself trigger a Pages build. Deployment behavior is not
redesigned here. A successful push must not be described as deployment evidence.

If the candidate workflow fails before pushing, stop and preserve diagnostics;
the remote snapshot remains unchanged. Roll back the workflow provisioning through
a reviewed revert if necessary. If incorrect artifacts were already published,
restore the coherent raw/processed snapshot, manifest, and matching website from a
known-good generation through a separately approved change. Do not restore isolated
files from mixed generations, force-push, or loosen numerical tolerances. Returning
to unpinned provisioning is an emergency fallback rather than a reproducible setup.

Completed Linux saved-input rehearsal evidence (Floor 5C):

- Ubuntu 24.04 x64; Python 3.13.16, uv 0.13.0, and Quarto 1.10.19.
- 73 tests passed before and after the saved-input rebuild.
- Baseline and regenerated-artifact validation passed.
- All three regenerated CSVs were byte-identical to the saved baseline.
- Three model-derived values differed by approximately 1.11e-16, within the
  unchanged existing tolerances.
- Full ten-page rendering and all existing website-output assertions passed.
- Nine staging records were inspected, all within the existing publishing allowlist.
- Original-checkout, copied-source, raw-input, and post-render data integrity passed.

Evidence is recorded in the successful temporary rehearsal run:
<https://github.com/pitzer-e/pitzer-e.github.io/actions/runs/38516252464>.
The temporary workflow has been removed from the final migration change.

Limited browser review of the downloaded Linux output passed for chart rendering,
map interaction, and table filtering. Narrow-viewport chart-title clipping remains
a known presentation caveat. This does not claim exhaustive visual equivalence.
No live HRSA downloads, authenticated publishing, or deployment were tested.

Merge readiness means that the implementation review and permanent three-platform
PR checks pass with only the production workflow and this documentation changed.
It does not authorize production activation. The saved-input rehearsal provides
regeneration evidence; the first live refresh, authenticated publication, and any
deployment verification require a separately approved operational plan. Merging
changes the scheduled workflow used by future runs, so merge approval must account
for its existing Monday schedule even if no manual dispatch is requested.
