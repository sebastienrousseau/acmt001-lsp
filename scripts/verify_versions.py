#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""Fail when the release version is restated differently anywhere.

Single source of truth: ``version`` in ``pyproject.toml``. The same string
must appear as:

* ``__version__`` in ``acmt001_lsp/__init__.py``;
* a ``## [X.Y.Z]`` heading in ``CHANGELOG.md``;
* the "Latest release: vX.Y.Z" callout in ``README.md``;
* the supported row of the version table in ``SECURITY.md``;
* the ``acmt001 >=`` floor in ``pyproject.toml`` and in every
  ``requirements/*.in`` that declares one (``requirements/runtime.in``
  must).

The acmt001 suite releases together at one version, core first, so the
floor on the core is this version: a lower one lets an older core, and
the older advisory floors it declares, resolve under this release. The
floor sat at ``acmt001 >= 0.0.5`` through the 0.0.9 release.

Standard library only, so the workflow needs no install.

Usage: python3 scripts/verify_versions.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: (file, pattern whose first group is the version restated there).
RESTATEMENTS = (
    ("acmt001_lsp/__init__.py", r'^__version__\s*=\s*"([^"]+)"'),
    ("README.md", r"Latest release: v(\d+\.\d+\.\d+)"),
    ("SECURITY.md", r"^\| `(\d+\.\d+\.\d+)` \| Latest released"),
)

#: Files that must declare an ``acmt001 >=`` floor.
FLOOR_REQUIRED = ("pyproject.toml", "requirements/runtime.in")

_FLOOR = re.compile(
    r'^\s*"?acmt001"?\s*(?:=\s*")?>=\s*([0-9][0-9.]*)', re.MULTILINE
)


def _read(root: Path, name: str) -> str:
    path = root / name
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _search(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1) if match else None


def pyproject_version(root: Path) -> str:
    """The version ``pyproject.toml`` declares: the source of truth."""
    version = _search(
        r'^version\s*=\s*"([^"]+)"', _read(root, "pyproject.toml")
    )
    if version is None:
        raise SystemExit("pyproject.toml has no version field")
    return version


def _floors(root: Path, expected: str) -> list[str]:
    names = {str(p.relative_to(root)) for p in root.glob("requirements/*.in")}
    out: list[str] = []
    for name in sorted(names | set(FLOOR_REQUIRED)):
        floors = _FLOOR.findall(_read(root, name))
        if not floors and name in FLOOR_REQUIRED:
            out.append(f"{name}: no acmt001>= floor")
        out.extend(
            f"{name}: acmt001>={floor}, the suite is at {expected}"
            for floor in floors
            if floor != expected
        )
    return out


def problems(root: Path = ROOT) -> list[str]:
    """Every restatement of the version that disagrees with pyproject."""
    expected = pyproject_version(root)
    out = [
        f"{name}: says {found}, pyproject.toml says {expected}"
        for name, pattern in RESTATEMENTS
        if (found := _search(pattern, _read(root, name))) != expected
    ]
    if f"\n## [{expected}]" not in "\n" + _read(root, "CHANGELOG.md"):
        out.append(f"CHANGELOG.md: no ## [{expected}] heading")
    return out + _floors(root, expected)


def main() -> int:
    """Compare every restatement of the version and report."""
    found = problems(ROOT)
    for problem in found:
        print(f"ERROR: {problem}")
    if found:
        return 1
    print(f"OK: every version source agrees on {pyproject_version(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
