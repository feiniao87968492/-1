#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
MANIFEST = ROOT / "data" / "raw_manifest.csv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_records() -> list[dict[str, str]]:
    records = []
    for path in sorted(p for p in RAW_DIR.rglob("*") if p.is_file() and p.name != ".gitkeep"):
        records.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "size_bytes": str(path.stat().st_size),
                "sha256": sha256(path),
            }
        )
    return records


def write_manifest(records: list[dict[str, str]]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "size_bytes", "sha256"])
        writer.writeheader()
        writer.writerows(records)


def read_manifest() -> list[dict[str, str]]:
    if not MANIFEST.exists():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST}")
    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or verify raw-data hashes")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    current = current_records()
    if args.verify:
        expected = read_manifest()
        if current != expected:
            print("[error] raw data differs from data/raw_manifest.csv")
            expected_map = {row["path"]: row for row in expected}
            current_map = {row["path"]: row for row in current}
            for path in sorted(set(expected_map) | set(current_map)):
                if expected_map.get(path) != current_map.get(path):
                    print(f"  changed: {path}")
            return 1
        print(f"[ok] verified {len(current)} raw files")
        return 0

    write_manifest(current)
    print(f"[ok] wrote {MANIFEST.relative_to(ROOT)} for {len(current)} raw files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
