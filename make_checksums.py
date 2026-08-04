# -*- coding: utf-8 -*-
"""SHA256SUMS manifest for the deposited release.

Without a manifest inside the release, a checksum stated anywhere else has
nothing fixed to point at, and a regeneration that silently changes bytes
cannot be told from one that reproduces them. This tool writes the manifest
(default) or verifies every file against it (--check), which is how the
bundled verifier proves that regenerating the ontology and the shapes
reproduces the archived bytes exactly.

Usage:
  python make_checksums.py           # (re)write SHA256SUMS
  python make_checksums.py --check   # verify all files against SHA256SUMS
Exit codes: 0 = OK, 1 = mismatch or missing file, 2 = manifest absent.
"""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "SHA256SUMS"
EXCLUDE_DIRS = {"__pycache__", ".git", ".ipynb_checkpoints"}
EXCLUDE_NAMES = {"SHA256SUMS", ".DS_Store", "Thumbs.db"}


def walk() -> list[Path]:
    out = []
    for f in sorted(HERE.rglob("*")):
        if not f.is_file():
            continue
        if EXCLUDE_DIRS & set(f.parts) or f.name in EXCLUDE_NAMES:
            continue
        if f.suffix in (".pyc", ".pyo"):
            continue
        out.append(f)
    return out


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write() -> int:
    files = walk()
    lines = [f"{sha256(f)}  {f.relative_to(HERE).as_posix()}" for f in files]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"SHA256SUMS written: {len(files)} files")
    return 0


def check() -> int:
    if not MANIFEST.exists():
        print("SHA256SUMS absent; run without --check first")
        return 2
    want = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        h, _, rel = line.partition("  ")
        want[rel] = h
    bad = 0
    seen = set()
    for f in walk():
        rel = f.relative_to(HERE).as_posix()
        seen.add(rel)
        if rel not in want:
            print(f"  UNLISTED  {rel}")
            bad += 1
        elif sha256(f) != want[rel]:
            print(f"  MISMATCH  {rel}")
            bad += 1
    for rel in sorted(set(want) - seen):
        print(f"  MISSING   {rel}")
        bad += 1
    print(f"checksum manifest: {len(want)} listed, {bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(check() if "--check" in sys.argv else write())
