#!/usr/bin/env python3
"""Generate metadata.json entries for LAS files."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable, List


@dataclass
class FileMetadata:
    name: str
    type: str
    size: str
    card: str
    owner: str

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "type": self.type,
            "size": self.size,
            "card": self.card,
            "owner": self.owner,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate metadata.json from LAS files under las-files/",
    )
    parser.add_argument(
        "--las-dir",
        default="las-files",
        type=Path,
        help="Directory containing *.las files (default: las-files)",
    )
    parser.add_argument(
        "--output",
        default="metadata.json",
        type=Path,
        help="Path to write the metadata JSON file (default: metadata.json)",
    )
    parser.add_argument(
        "--owner",
        default=os.environ.get("GITHUB_ACTOR", ""),
        help="GitHub handle recorded as the uploader. Defaults to GITHUB_ACTOR env var.",
    )
    return parser.parse_args()


def format_size(bytes_size: int) -> str:
    """Return the size in megabytes with a single decimal place."""
    size_mb = Decimal(bytes_size) / Decimal(1024 * 1024)
    rounded = size_mb.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return f"{rounded}MB"


def extract_name_and_card(stem: str) -> tuple[str, str]:
    if "_" not in stem:
        return stem, ""
    name, card = stem.rsplit("_", 1)
    return name, card


def collect_metadata(paths: Iterable[Path], owner: str) -> List[FileMetadata]:
    records: List[FileMetadata] = []
    for path in sorted(paths):
        if path.name.startswith("."):
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() != ".las":
            continue

        name, card = extract_name_and_card(path.stem)
        records.append(
            FileMetadata(
                name=name,
                type=path.suffix.lstrip(".").upper(),
                size=format_size(path.stat().st_size),
                card=card,
                owner=owner or "Unknown",
            ),
        )
    return sorted(records, key=lambda item: item.name)


def write_metadata(entries: Iterable[FileMetadata], destination: Path) -> None:
    payload = {"files": [entry.to_dict() for entry in entries]}
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    las_dir: Path = args.las_dir
    if not las_dir.exists():
        raise SystemExit(f"LAS directory does not exist: {las_dir}")

    entries = collect_metadata(las_dir.iterdir(), owner=args.owner)
    write_metadata(entries, args.output)


if __name__ == "__main__":
    main()
