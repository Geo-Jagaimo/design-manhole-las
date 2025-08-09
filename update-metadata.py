#!/usr/bin/env python3
import json
from pathlib import Path

def get_file_metadata(file_path):
    """Extract metadata from a file according to specifications"""
    file_path = Path(file_path)
    
    # name: filename without extension
    name = file_path.stem
    
    # type: extension (uppercase, without dot)
    file_type = file_path.suffix.lstrip('.').upper()
    
    # size: file size in megabytes
    size_bytes = file_path.stat().st_size
    size_mb = round(size_bytes / (1024 * 1024), 1)
    size = f"{size_mb}MB"
    
    # card: extract card number after underscore, empty if no underscore
    card = ""
    if '_' in name:
        card = name.split('_', 1)[1]  # Everything after first underscore
    
    return {
        "name": name,
        "type": file_type,
        "size": size,
        "card": card
    }

def update_metadata():
    """Update metadata.json with current files in las-files directory"""
    las_files_dir = Path("las-files")
    metadata_file = Path("metadata.json")
    
    if not las_files_dir.exists():
        print(f"Directory {las_files_dir} not found")
        return
    
    # Get all files in las-files directory
    files_metadata = []
    for file_path in las_files_dir.iterdir():
        if file_path.is_file():
            metadata = get_file_metadata(file_path)
            files_metadata.append(metadata)
    
    # Sort by name for consistent output
    files_metadata.sort(key=lambda x: x['name'])
    
    # Create metadata structure
    metadata = {
        "files": files_metadata
    }
    
    # Write to metadata.json
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    print(f"Updated metadata.json with {len(files_metadata)} files")

if __name__ == "__main__":
    update_metadata()