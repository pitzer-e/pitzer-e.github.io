"""Validate saved artifacts and render a disposable tracked-file copy."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(*args, cwd=ROOT, env=None):
    subprocess.run(args, cwd=cwd, env=env, check=True)


def main():
    quarto = shutil.which("quarto")
    if not quarto:
        raise SystemExit("Install Quarto 1.10.19 and add it to PATH.")
    version = subprocess.check_output([quarto, "--version"], text=True).strip()
    if version != (ROOT / ".quarto-version").read_text().strip():
        raise SystemExit(f"Unexpected Quarto version: {version}")
    if sys.version_info[:3] != (3, 13, 16):
        raise SystemExit("Use Python 3.13.16 via uv sync --locked.")
    files = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT
    ).decode().split("\0")
    files = [p for p in files if p]
    before = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in files}
    with tempfile.TemporaryDirectory(prefix="portfolio-validation-") as tmp:
        work = Path(tmp) / "site"
        work.mkdir()
        for name in files:
            if Path(name).parts[0] in {"docs", ".github"}:
                continue
            target = work / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        env = os.environ.copy()
        env.update(PYTHONDONTWRITEBYTECODE="1", QUARTO_PYTHON=sys.executable,
                   MPLCONFIGDIR=str(Path(tmp) / "matplotlib"),
                   JUPYTER_CONFIG_DIR=str(Path(tmp) / "jupyter-config"),
                   JUPYTER_DATA_DIR=str(Path(tmp) / "jupyter-data"),
                   JUPYTER_RUNTIME_DIR=str(Path(tmp) / "jupyter-runtime"),
                   IPYTHONDIR=str(Path(tmp) / "ipython"))
        run(sys.executable, "-m", "pytest", "-p", "no:cacheprovider",
            "projects/oregon-fqhc/tests/", cwd=work, env=env)
        run(sys.executable, "projects/oregon-fqhc/scripts/4_analyze_correlations.py",
            cwd=work, env=env)
        data = {p: hashlib.sha256((work / p).read_bytes()).hexdigest()
                for p in files if "/data/" in p}
        run(quarto, "render", cwd=work, env=env)
        for p, digest in data.items():
            if hashlib.sha256((work / p).read_bytes()).hexdigest() != digest:
                raise SystemExit(f"Render changed saved data: {p}")
    for p, digest in before.items():
        if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"Validation changed checkout file: {p}")
    print("Tests, saved snapshot, isolated render, and unchanged hashes verified.")


if __name__ == "__main__":
    main()
