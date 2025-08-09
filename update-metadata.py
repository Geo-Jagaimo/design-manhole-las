#!/usr/bin/env python3
"""
LASファイルのメタデータを自動生成・更新するスクリプト
"""

import os
import json
import datetime
from pathlib import Path


def get_file_size_mb(file_path):
    """ファイルサイズをMB単位で取得"""
    size_bytes = os.path.getsize(file_path)
    size_mb = size_bytes / (1024 * 1024)
    return f"{size_mb:.1f}MB"


def get_next_card_number(existing_cards):
    """次のカード番号を生成"""
    if not existing_cards:
        return "A001"
    
    # 最大の番号を見つける
    max_num = 0
    for card in existing_cards:
        if card.startswith("A"):
            try:
                num = int(card[1:])
                max_num = max(max_num, num)
            except ValueError:
                continue
    
    return f"A{max_num + 1:03d}"


def update_metadata():
    """メタデータを更新"""
    las_dir = Path("las-files")
    metadata_file = Path("metadata.json")
    
    # 既存のメタデータを読み込み
    if metadata_file.exists():
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        metadata = {"files": []}
    
    # 既存のファイル名とカード番号を取得
    existing_files = {file_info["name"] for file_info in metadata["files"]}
    existing_cards = {file_info["card"] for file_info in metadata["files"]}
    
    # LASファイルディレクトリをスキャン
    if not las_dir.exists():
        print("las-filesディレクトリが見つかりません")
        return
    
    new_files_added = False
    
    for las_file in las_dir.glob("*.las"):
        filename = las_file.name
        
        # 既存のファイルはスキップ
        if filename in existing_files:
            continue
        
        # 新しいファイルのメタデータを作成
        file_info = {
            "name": filename,
            "size": get_file_size_mb(las_file),
            "date": datetime.date.today().strftime("%Y-%m-%d"),
            "card": get_next_card_number(existing_cards)
        }
        
        metadata["files"].append(file_info)
        existing_cards.add(file_info["card"])
        new_files_added = True
        
        print(f"新しいファイルを追加: {filename} ({file_info['size']}, {file_info['card']})")
    
    # メタデータを保存
    if new_files_added:
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"metadata.jsonを更新しました")
    else:
        print("新しいLASファイルは見つかりませんでした")


if __name__ == "__main__":
    update_metadata()