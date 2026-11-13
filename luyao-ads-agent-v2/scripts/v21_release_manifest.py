#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "releases/v2.1/MANIFEST.sha256"
IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    ".pytest_cache",
    "__pycache__",
    "imports",
    "runtime",
    "outputs",
    "node_modules",
    "dist",
    ".wrangler",
    ".vinext",
    ".next",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_managed_file(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if path == MANIFEST:
        return False
    if any(part in IGNORED_DIRECTORIES for part in relative.parts):
        return False
    if path.name == ".DS_Store" or path.name.startswith(("._", "~$")):
        return False
    return path.is_file()


def managed_files() -> dict[str, Path]:
    return {
        path.relative_to(ROOT).as_posix(): path
        for path in ROOT.rglob("*")
        if is_managed_file(path)
    }


def write_manifest() -> int:
    files = managed_files()
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{sha256(files[relative])}  {relative}" for relative in sorted(files)]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    total_bytes = sum(path.stat().st_size for path in files.values())
    print(
        f"V2.1 runtime manifest written: files={len(files)}, "
        f"bytes={total_bytes}, manifest_sha256={sha256(MANIFEST)}"
    )
    return 0


def read_manifest() -> dict[str, str]:
    if not MANIFEST.is_file():
        raise FileNotFoundError(f"V2.1 runtime manifest does not exist: {MANIFEST}")
    records: dict[str, str] = {}
    for line_number, raw_line in enumerate(MANIFEST.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            digest, relative = raw_line.split("  ", 1)
        except ValueError as exc:
            raise ValueError(f"invalid manifest line {line_number}: {raw_line}") from exc
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError(f"invalid SHA-256 at manifest line {line_number}")
        if relative in records:
            raise ValueError(f"duplicate manifest path: {relative}")
        records[relative] = digest
    return records


def verify_manifest() -> int:
    expected = read_manifest()
    current = managed_files()
    missing = sorted(set(expected) - set(current))
    extra = sorted(set(current) - set(expected))
    mismatched = sorted(
        relative
        for relative in set(expected) & set(current)
        if sha256(current[relative]) != expected[relative]
    )
    if missing or extra or mismatched:
        print("V2.1 runtime verification failed")
        if missing:
            print("missing:", ", ".join(missing))
        if extra:
            print("extra:", ", ".join(extra))
        if mismatched:
            print("mismatched:", ", ".join(mismatched))
        return 1
    print(
        f"V2.1 runtime verification passed: files={len(expected)}, "
        f"manifest_sha256={sha256(MANIFEST)}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Write or verify the frozen V2.1 runtime manifest")
    parser.add_argument("--write", action="store_true", help="rewrite the V2.1 runtime manifest")
    args = parser.parse_args()
    return write_manifest() if args.write else verify_manifest()


if __name__ == "__main__":
    raise SystemExit(main())
