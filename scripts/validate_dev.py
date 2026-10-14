"""Validate saved artifacts and render a disposable tracked-file copy."""
from contextlib import contextmanager
import hashlib
import os
import platform
import struct
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(*args, cwd=ROOT, env=None):
    subprocess.run(args, cwd=cwd, env=env, check=True)


def fingerprints(root, files):
    return {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in files}


def verify_integrity(root, before, label):
    changed = [p for p, digest in before.items()
               if not (root / p).is_file()
               or hashlib.sha256((root / p).read_bytes()).hexdigest() != digest]
    if changed:
        raise RuntimeError(f"{label} changed: {', '.join(changed)}")
    print(f"{label} integrity verified.", flush=True)


@contextmanager
def integrity_guard(root, before, label):
    """Check integrity on every exit without masking the primary failure."""
    try:
        yield
    except BaseException as error:
        try:
            verify_integrity(root, before, label)
        except Exception as violation:
            error.add_note(str(violation))
            print(f"Additional integrity violation: {violation}", file=sys.stderr, flush=True)
        raise
    else:
        verify_integrity(root, before, label)


def verify_platform():
    system = platform.system()
    os_name = {"Darwin": "macOS", "Linux": "Linux", "Windows": "Windows"}.get(system)
    machine = platform.machine().lower()
    arch = {"arm64": "ARM64", "aarch64": "ARM64",
            "amd64": "X64", "x86_64": "X64"}.get(machine)
    expected_os = os.environ.get("EXPECTED_RUNNER_OS", os_name)
    expected_arch = os.environ.get("EXPECTED_RUNNER_ARCH", arch)
    if not os_name or not arch or struct.calcsize("P") != 8:
        raise SystemExit(f"Unsupported interpreter architecture: {system}/{machine}")
    if (os_name, arch) != (expected_os, expected_arch):
        raise SystemExit(f"Interpreter platform mismatch: {os_name}/{arch}")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        if not all(os.environ.get(k) for k in ("EXPECTED_RUNNER_OS", "EXPECTED_RUNNER_ARCH")):
            raise SystemExit("CI must declare the expected runner platform.")
        if (os.environ.get("RUNNER_OS"), os.environ.get("RUNNER_ARCH")) != (expected_os, expected_arch):
            raise SystemExit("Runner platform does not match the validation matrix.")
    print(f"Interpreter: {sys.executable}; {platform.python_version()}; {os_name}/{arch}; 64-bit", flush=True)


def main():
    files = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT
    ).decode().split("\0")
    files = [p for p in files if p]
    before = fingerprints(ROOT, files)
    with integrity_guard(ROOT, before, "Original tracked checkout"):
        verify_platform()
        quarto = shutil.which("quarto")
        if not quarto:
            raise SystemExit("Install Quarto 1.10.19 and add it to PATH.")
        version = subprocess.check_output([quarto, "--version"], text=True).strip()
        if version != (ROOT / ".quarto-version").read_text().strip():
            raise SystemExit(f"Unexpected Quarto version: {version}")
        if sys.version_info[:3] != (3, 13, 16):
            raise SystemExit("Use Python 3.13.16 via uv sync --locked.")
        print(f"Quarto: {quarto}; {version}", flush=True)
        with tempfile.TemporaryDirectory(prefix="portfolio-validation-") as tmp:
            work = Path(tmp) / "site"
            work.mkdir()
            if work.resolve().is_relative_to(ROOT):
                raise RuntimeError("Validation directory must be outside the checkout.")
            print(f"Isolated validation directory: {work}", flush=True)
            for name in files:
                if Path(name).parts[0] in {"docs", ".github"}:
                    continue
                target = work / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / name, target)
            data = fingerprints(work, [p for p in files if "/data/" in p])
            env = os.environ.copy()
            env.update(PYTHONDONTWRITEBYTECODE="1", QUARTO_PYTHON=sys.executable,
                       MPLCONFIGDIR=str(Path(tmp) / "matplotlib"),
                       JUPYTER_CONFIG_DIR=str(Path(tmp) / "jupyter-config"),
                       JUPYTER_DATA_DIR=str(Path(tmp) / "jupyter-data"),
                       JUPYTER_RUNTIME_DIR=str(Path(tmp) / "jupyter-runtime"),
                       IPYTHONDIR=str(Path(tmp) / "ipython"))
            with integrity_guard(work, data, "Copied saved data"):
                run(sys.executable, "-m", "pytest", "-p", "no:cacheprovider",
                    "projects/oregon-fqhc/tests/", cwd=work, env=env)
                run(sys.executable, "projects/oregon-fqhc/scripts/4_analyze_correlations.py",
                    cwd=work, env=env)
                run(quarto, "render", cwd=work, env=env)
    print("Tests, saved snapshot, isolated render, and unchanged hashes verified.")


if __name__ == "__main__":
    main()
