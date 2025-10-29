"""
LAS群から重心を計算して index.geojson を生成するユーティリティ。
- 各LASはヘッダのSRSを使い、WGS84(EPSG:4326)へ再投影してから重心（平均）を算出
- 失敗したファイルはスキップし、最後に集約GeoJSONを書き出し
- 任意で in_srs を明示可能（SRSが入っていないLAS向け）
"""

import argparse
import glob
import json
import sys
from pathlib import Path

try:
    import pdal  # conda-forge: 'pdal' (Pythonバインディング)
except Exception as e:
    print(
        "ERROR: PythonのPDALバインディングが見つかりません。conda-forge から 'pdal' を入れてください。",
        file=sys.stderr,
    )
    print("例: mamba install -c conda-forge pdal", file=sys.stderr)
    raise

FEATURE_TPL = {
    "type": "Feature",
    "properties": {"source_file": None, "z": None},
    "geometry": {"type": "Point", "coordinates": [None, None]},
}
FC_TPL = {"type": "FeatureCollection", "features": []}


def _extract_dimension_averages(statistic_node) -> dict:
    """
    PDALのfilters.stats出力から平均値を取り出す。
    バージョンにより配列/辞書のいずれかになるので両対応する。
    """
    averages: dict[str, float] = {}
    if isinstance(statistic_node, list):
        for entry in statistic_node:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            avg = entry.get("average")
            if name and avg is not None:
                averages[name] = avg
        return averages

    if isinstance(statistic_node, dict):
        # 値が入れ子の辞書 ({"X": {...}, "Y": {...}}) と単独辞書の両方を面倒見る
        if "name" in statistic_node and "average" in statistic_node:
            name = statistic_node.get("name")
            avg = statistic_node.get("average")
            if name and avg is not None:
                averages[name] = avg
        for key, value in statistic_node.items():
            if not isinstance(value, dict):
                continue
            name = value.get("name") or key
            avg = value.get("average")
            if name and avg is not None:
                averages[name] = avg
    return averages


def build_pipeline(filename: str, in_srs: str | None, out_srs: str) -> str:
    """
    PDAL Pipeline JSON（文字列）を構築。
    - in_srs があれば readers.las に override_srs / filters.reprojection.in_srs を明示
    - なければLASヘッダのSRSを使用（filters.reprojectionは out_srs だけ）
    """
    if in_srs:
        pipeline = {
            "pipeline": [
                {"type": "readers.las", "filename": filename, "override_srs": in_srs},
                {"type": "filters.reprojection", "in_srs": in_srs, "out_srs": out_srs},
                {"type": "filters.stats", "dimensions": "X,Y,Z"},
                {"type": "writers.null"},
            ]
        }
    else:
        pipeline = {
            "pipeline": [
                filename,
                {"type": "filters.reprojection", "out_srs": out_srs},
                {"type": "filters.stats", "dimensions": "X,Y,Z"},
                {"type": "writers.null"},
            ]
        }
    return json.dumps(pipeline)


def centroid_for_file(
    path: Path, in_srs: str | None, out_srs: str
) -> tuple[float, float, float] | None:
    """
    1ファイルの重心 (X,Y,Z) を返す（lon, lat, z）。
    失敗時は None。
    """
    pipe_json = build_pipeline(str(path), in_srs, out_srs)
    try:
        pipe = pdal.Pipeline(pipe_json)
        pipe.validate()  # 検証
        pipe.execute()  # 実行
        meta = json.loads(pipe.metadata)  # str -> dict
        stats_node = (
            meta.get("metadata", {}).get("filters.stats", {}).get("statistic", [])
        )
        avg = _extract_dimension_averages(stats_node)
        x = avg.get("X") or avg.get("x")
        y = avg.get("Y") or avg.get("y")
        z = avg.get("Z") or avg.get("z")
        if x is None or y is None:
            return None
        return float(x), float(y), float(z) if z is not None else None
    except Exception as e:
        # ここで詳しい原因を出力
        print(f"[WARN] PDAL failed on {path}: {e}", file=sys.stderr)
        return None


def main():
    ap = argparse.ArgumentParser(
        description="Compute centroids from LAS and build index.geojson"
    )
    ap.add_argument(
        "--glob", default="las-files/*.las", help="LAS のグロブ。例: 'las-files/*.las'"
    )
    ap.add_argument("--out", default="index.geojson", help="出力GeoJSONパス")
    ap.add_argument(
        "--in-srs",
        default=None,
        help="入力SRSを明示（例: EPSG:32654）。LASヘッダが空/不正な場合に使用",
    )
    ap.add_argument("--out-srs", default="EPSG:4326", help="出力SRS（既定: EPSG:4326）")
    ap.add_argument("--pretty", action="store_true", help="整形（インデント）して出力")
    args = ap.parse_args()

    files = sorted({Path(p) for p in glob.glob(args.glob)})
    if not files:
        print(f"[INFO] No LAS matched: {args.glob}", file=sys.stderr)

    fc = dict(FC_TPL)
    fc["features"] = []

    for f in files:
        if not f.exists():
            print(f"[WARN] Not found: {f}", file=sys.stderr)
            continue

        print(f"[INFO] Processing: {f}")
        c = centroid_for_file(f, args.in_srs, args.out_srs)
        if c is None:
            print(f"[WARN] Skip (centroid unavailable): {f}", file=sys.stderr)
            continue

        x, y, z = c if len(c) == 3 else (c[0], c[1], None)
        feat = json.loads(json.dumps(FEATURE_TPL))  # deepcopy簡易版
        feat["properties"]["source_file"] = str(f)
        feat["properties"]["z"] = z
        feat["geometry"]["coordinates"] = [x, y]
        fc["features"].append(feat)

    out_path = Path(args.out)
    out_path.write_text(
        json.dumps(fc, indent=2 if args.pretty else None, ensure_ascii=False)
    )
    print(f"[DONE] Wrote {out_path} with {len(fc['features'])} features")


if __name__ == "__main__":
    main()
