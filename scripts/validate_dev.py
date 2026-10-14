"""Validate saved artifacts and render a disposable tracked-file copy."""
from contextlib import contextmanager
import hashlib
from html.parser import HTMLParser
import json
import posixpath
import os
import platform
import struct
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit

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


EXPECTED_PAGES = {
    "index.html", "projects.html", "dashboards.html",
    "dashboards/health-landscape/index.html",
    "projects/clinic-forecasting/index.html",
    "projects/clinic-forecasting/about.html",
    "projects/oregon-fqhc/index.html", "projects/oregon-fqhc/about.html",
    "projects/penguins/index.html", "projects/welcome/index.html",
}


class WebsiteLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.hrefs.extend(value for key, value in attrs
                              if key == "href" and value is not None)


def local_target(page, href):
    url = urlsplit(href)
    if url.scheme or url.netloc:
        return None
    path = unquote(url.path)
    if path.startswith("/"):
        return posixpath.normpath(path.lstrip("/"))
    return posixpath.normpath(posixpath.join(posixpath.dirname(page), path))


def verify_website(work):
    output = work / "docs"
    actual = {p.relative_to(output).as_posix() for p in output.rglob("*.html")}
    if actual != EXPECTED_PAGES:
        raise RuntimeError(f"Website page mismatch: missing={sorted(EXPECTED_PAGES - actual)}, "
                           f"unexpected={sorted(actual - EXPECTED_PAGES)}")
    forbidden = [p.relative_to(output).as_posix() for p in output.rglob("*")
                 if p.is_file() and (p.stem.lower() == "development"
                                     or "notes" in p.relative_to(output).parts
                                     or p.name.startswith("engineering-checkpoint"))]
    if forbidden:
        raise RuntimeError(f"Engineering documentation published: {forbidden}")
    search = json.loads((output / "search.json").read_text(encoding="utf-8"))
    if not isinstance(search, list) or not search:
        raise RuntimeError("Website search metadata is missing or malformed.")
    for entry in search:
        if not isinstance(entry, dict) or not isinstance(entry.get("href"), str):
            raise RuntimeError("Malformed website search entry.")
        if local_target("index.html", entry["href"]) not in EXPECTED_PAGES:
            raise RuntimeError(f"Unexpected search target: {entry['href']}")
    search_text = json.dumps(search).lower()
    if any(marker in search_text for marker in
           ("development.md", "development.html", "engineering-checkpoint",
            "reproducible development environment", "platform verification status")):
        raise RuntimeError("Engineering documentation appeared in website search.")

    def require_links(page, expected):
        parser = WebsiteLinks()
        parser.feed((output / page).read_text(encoding="utf-8"))
        targets = {local_target(page, href) for href in parser.hrefs}
        missing = expected - targets
        if missing:
            raise RuntimeError(f"Missing links in {page}: {sorted(missing)}")

    navigation = {"index.html", "projects.html", "dashboards.html"}
    for page in EXPECTED_PAGES:
        require_links(page, navigation)
    require_links("projects.html", {
        f"projects/{case}/index.html" for case in
        ("oregon-fqhc", "clinic-forecasting", "penguins", "welcome")
    })
    contract = "projects/oregon-fqhc/README.md"
    require_links("projects/oregon-fqhc/about.html", {contract})
    if (output / contract).read_bytes() != (work / contract).read_bytes():
        raise RuntimeError("Published FQHC data contract differs from its source.")
    print("Rendering acceptance verified: exactly ten HTML pages; engineering documentation "
          "excluded from output/search; navigation and case-study links intact; "
          "linked FQHC data contract byte-identical.", flush=True)


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
                verify_website(work)
    print("Tests, saved snapshot, isolated render, and unchanged hashes verified.")


if __name__ == "__main__":
    main()
