"""Write Formula/lcode.rb for an lcode-cli release on PyPI.

    python scripts/update_formula.py            # the newest release that is at least a day old
    python scripts/update_formula.py 0.4.0      # a specific release

The Python dependencies are resolved with pip (run this with the same Python version as the
formula's `python@3.x` dependency) and pinned as resources, using their source distributions, as
Homebrew requires. `certifi` comes from Homebrew's own formula instead.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PACKAGE = "lcode-cli"
COOLDOWN = dt.timedelta(days=1)  # like Homebrew, don't take packages uploaded in the last day
FROM_HOMEBREW = {"certifi"}  # provided by `depends_on "certifi"`
FORMULA = Path(__file__).resolve().parent.parent / "Formula" / "lcode.rb"

TEMPLATE = """\
class Lcode < Formula
  include Language::Python::Virtualenv

  desc "Local-first terminal coding agent powered by open-weight models via Ollama"
  homepage "https://nasser1941.github.io/lcode/"
  url "{url}"
  sha256 "{sha256}"
  license "MIT"

  depends_on "certifi"
  depends_on "python@3.14"
  depends_on "ripgrep"
{resources}
  def install
    virtualenv_install_with_resources
  end

  def caveats
    <<~EOS
      lcode runs models with Ollama. If you don't have it yet:
        brew install ollama
        brew services start ollama
      Then choose and download the best model for this machine:
        lcode setup
    EOS
  end

  test do
    assert_match "lcode #{{version}}", shell_output("#{{bin}}/lcode --version")
    assert_match "qwen3.6-35b", shell_output("#{{bin}}/lcode models")
  end
end
"""


def pypi(name: str, version: str | None = None) -> dict:
    url = f"https://pypi.org/pypi/{name}/{version}/json" if version else f"https://pypi.org/pypi/{name}/json"
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def sdist(name: str, version: str) -> tuple[str, str]:
    for file in pypi(name, version)["urls"]:
        if file["packagetype"] == "sdist":
            return file["url"], file["digests"]["sha256"]
    raise SystemExit(f"{name} {version} has no source distribution on PyPI")


def latest_settled() -> str:
    """The newest lcode-cli release whose files were uploaded at least COOLDOWN ago."""
    now = dt.datetime.now(dt.timezone.utc)
    releases = pypi(PACKAGE)["releases"]
    settled = []
    for version, files in releases.items():
        if files and not any(f.get("yanked") for f in files):
            uploaded = max(dt.datetime.fromisoformat(f["upload_time_iso_8601"].replace("Z", "+00:00")) for f in files)
            if now - uploaded >= COOLDOWN:
                settled.append(version)
    if not settled:
        raise SystemExit("no lcode-cli release is old enough yet")
    return max(settled, key=key)


def dependencies(version: str, cooldown: bool) -> list[tuple[str, str]]:
    """lcode-cli's dependencies for this Python, as resolved by pip: [(name, version)].

    With `cooldown`, pip only considers files uploaded at least a day ago, like Homebrew's
    `brew update-python-resources`, so a just-published (possibly malicious) release isn't picked up.
    """
    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--quiet",
        "--disable-pip-version-check",
        "--dry-run",
        "--ignore-installed",
        "--report",
        "-",
        f"{PACKAGE}=={version}",
    ]
    if cooldown:
        command.insert(4, "--uploaded-prior-to=P1D")
    else:
        command.insert(4, "--no-cache-dir")
    for attempt in range(6):  # PyPI's index can lag a few minutes behind a release
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode == 0 or "No matching distribution" not in result.stderr or cooldown:
            break
        time.sleep(30)
    if result.returncode != 0:
        raise SystemExit(f"pip couldn't resolve {PACKAGE}=={version}:\n{result.stderr.strip()}")
    report = result.stdout
    found = [
        (i["metadata"]["name"].lower().replace("_", "-"), i["metadata"]["version"])
        for i in json.loads(report)["install"]
    ]
    return sorted((n, v) for n, v in found if n != PACKAGE and n not in FROM_HOMEBREW)


def render(version: str, cooldown: bool = True) -> str:
    url, sha256 = sdist(PACKAGE, version)
    blocks = []
    for name, dep_version in dependencies(version, cooldown):
        dep_url, dep_sha = sdist(name, dep_version)
        blocks.append(f'\n  resource "{name}" do\n    url "{dep_url}"\n    sha256 "{dep_sha}"\n  end\n')
    return TEMPLATE.format(url=url, sha256=sha256, resources="".join(blocks))


def key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def current() -> str | None:
    """The version in the formula now."""
    match = re.search(r"lcode_cli-([0-9.]+)\.tar\.gz", FORMULA.read_text()) if FORMULA.exists() else None
    return match.group(1) if match else None


def main() -> None:
    if len(sys.argv) > 1:
        # A version a maintainer chose: it may be less than a day old, so no cooldown.
        version, cooldown = sys.argv[1], False
    else:
        version, cooldown = latest_settled(), True
        if current() and key(version) <= key(current()):
            print(f"lcode {current()}: already up to date (newest release a day old: {version})")
            if "GITHUB_OUTPUT" in os.environ:
                with open(os.environ["GITHUB_OUTPUT"], "a") as out:
                    out.write(f"changed=false\nversion={current()}\n")
            return
    text = render(version, cooldown)
    changed = not FORMULA.exists() or FORMULA.read_text() != text
    FORMULA.write_text(text)
    print(f"lcode {version}: {'updated' if changed else 'already up to date'}")
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as out:
            out.write(f"changed={'true' if changed else 'false'}\nversion={version}\n")


if __name__ == "__main__":
    main()
