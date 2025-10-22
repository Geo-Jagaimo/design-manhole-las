#!/usr/bin/env python3
import json
import os
from pathlib import Path


def get_file_metadata(file_path, owner=None):
    """Extract metadata from a file according to specifications"""
    file_path = Path(file_path)

    stem = file_path.stem
    name = stem.split("_")[0] if "_" in stem else stem

    file_type = file_path.suffix.lstrip(".").upper()

    size_bytes = file_path.stat().st_size
    size_mb = round(size_bytes / (1024 * 1024), 1)
    size = f"{size_mb}MB"

    # card number
    card = ""
    if "_" in stem:
        card = stem.split("_", 1)[1]  # Everything after first underscore

    return {"name": name, "type": file_type, "size": size, "card": card, "owner": owner}


def update_metadata():
    """Update metadata.json with current files in las-files directory"""
    las_files_dir = Path("las-files")
    metadata_file = Path("metadata.json")

    if not las_files_dir.exists():
        print(f"Directory {las_files_dir} not found")
        return

    # Get owner from environment variable (set by GitHub Actions)
    owner = os.environ.get("GITHUB_ACTOR")

    files_metadata = []
    for file_path in las_files_dir.iterdir():
        if file_path.is_file():
            metadata = get_file_metadata(file_path, owner)
            files_metadata.append(metadata)

    files_metadata.sort(key=lambda x: x["name"])

    metadata = {"files": files_metadata}

    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"Updated metadata.json with {len(files_metadata)} files")


if __name__ == "__main__":
    update_metadata()
