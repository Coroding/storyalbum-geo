from __future__ import annotations

import argparse

from geo_album_utils import META_DIR, cluster_photo_records, ensure_geo_dirs, read_json, write_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold-m", type=int, default=200)
    args = parser.parse_args()
    ensure_geo_dirs()
    manifest = read_json(META_DIR / "photo_manifest.json", default=[])
    stops = cluster_photo_records(manifest, threshold_m=args.threshold_m)
    output = {
        "type": "geo_stops_raw",
        "cluster_threshold_m": args.threshold_m,
        "stop_count": len(stops),
        "fallback_config": None,
        "stops": stops,
    }
    if not stops:
        output["fallback_config"] = {
            "reason": "没有读取到带 GPS 的照片",
            "message": "请补充带 GPS 的照片，或在 geo_stops_raw.json 中手动添加地点坐标。",
        }
    write_json(META_DIR / "geo_stops_raw.json", output)
    print(f"gps_photo_count={sum(1 for row in manifest if row.get('has_gps'))}")
    print(f"stop_count={len(stops)}")
    print(f"output={META_DIR / 'geo_stops_raw.json'}")


if __name__ == "__main__":
    main()

