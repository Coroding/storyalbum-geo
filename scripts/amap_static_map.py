from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import urlopen

from geo_album_utils import (
    CACHE_DIR,
    DEMO_DATA_DIR,
    MAP_AMAP_DIR,
    MAP_STYLED_DIR,
    META_DIR,
    PROJECT_ROOT,
    append_call_log,
    ensure_geo_dirs,
    get_amap_key,
    mask_amap_key,
    read_json,
    relative_to_demo,
    write_json,
)


STATIC_URL = "https://restapi.amap.com/v3/staticmap"
PNG_PATH = MAP_AMAP_DIR / "geo_route_amap.png"
URL_PATH = MAP_AMAP_DIR / "geo_route_amap_url.txt"
METADATA_PATH = MAP_AMAP_DIR / "geo_route_amap_metadata.json"
CALL_LOG = CACHE_DIR / "amap_call_log.json"
OVERLAY_LIMIT = 10


def _load_stops() -> list[dict]:
    enriched = read_json(META_DIR / "geo_stops_enriched.json", default=None)
    if enriched:
        return enriched.get("stops", [])
    raw = read_json(META_DIR / "geo_stops_raw.json", default={"stops": []})
    return raw.get("stops", [])


def _zoom_for_span(stops: list[dict]) -> int:
    lats = [float(stop["centroid_wgs84"]["lat"]) for stop in stops]
    lngs = [float(stop["centroid_wgs84"]["lng"]) for stop in stops]
    span = max(max(lats) - min(lats), max(lngs) - min(lngs))
    if span < 0.02:
        return 14
    if span < 0.08:
        return 13
    if span < 0.2:
        return 12
    if span < 0.5:
        return 10
    return 9


def _build_url(key: str, stops: list[dict]) -> str:
    coords = [(round(float(stop["centroid_wgs84"]["lng"]), 6), round(float(stop["centroid_wgs84"]["lat"]), 6)) for stop in stops]
    center_lng = sum(lng for lng, _lat in coords) / len(coords)
    center_lat = sum(lat for _lng, lat in coords) / len(coords)
    markers = []
    labels = []
    marker_labels = "123456789A"
    for index, stop in enumerate(stops[:OVERLAY_LIMIT], start=1):
        lng, lat = coords[index - 1]
        marker_label = marker_labels[index - 1]
        markers.append(f"mid,0x2f80ed,{marker_label}:{lng:.6f},{lat:.6f}")
        labels.append(f"{index:02d}.{str(stop.get('name') or '地点')[:8]},0,1,14,0xFFFFFF,0x2f80ed:{lng:.6f},{lat:.6f}")
    paths = "8,0x38a169,0.75,,:{}".format(";".join(f"{lng},{lat}" for lng, lat in coords))
    params = {
        "key": key,
        "location": f"{center_lng:.6f},{center_lat:.6f}",
        "zoom": str(_zoom_for_span(stops)),
        "size": "750*1000",
        "scale": "2",
        "markers": "|".join(markers),
        "labels": "|".join(labels),
        "paths": paths,
    }
    return f"{STATIC_URL}?{urlencode(params, safe='*,;:|,.')}"


def _fallback() -> None:
    subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts" / "stylize_geo_route.py")], check=False)


def _update_album_map_preference(preferred: str) -> None:
    album_path = DEMO_DATA_DIR / "geo_album.json"
    album = read_json(album_path, default=None)
    if not album:
        return
    album.setdefault("map", {})
    album["map"]["preferred"] = preferred
    album["map"]["amapStatic"] = relative_to_demo(PNG_PATH)
    album["map"]["fallback"] = relative_to_demo(MAP_STYLED_DIR / "cute_geo_route.svg")
    write_json(album_path, album)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument("--max-calls", type=int, default=50)
    args = parser.parse_args()

    ensure_geo_dirs()
    stops = [stop for stop in _load_stops() if (stop.get("centroid_wgs84") or {}).get("lat") is not None]
    if len(stops) < 1:
        print("not_enough_coordinates=1")
        _fallback()
        return

    planned = 0 if PNG_PATH.exists() and not args.force_refresh else 1
    if args.dry_run:
        print(f"stops={len(stops)}")
        print(f"planned_api_calls={min(planned, args.max_calls)}")
        print(f"existing_png={PNG_PATH.exists()}")
        return

    if PNG_PATH.exists() and not args.force_refresh:
        print(f"using_existing={PNG_PATH}")
        _update_album_map_preference("amap_static")
        return
    if args.max_calls <= 0:
        print("max_calls=0; generating fallback route")
        _fallback()
        _update_album_map_preference("cute_route")
        return

    amap_key = get_amap_key()
    if not amap_key:
        print("AMap key is missing; generating fallback route")
        _fallback()
        _update_album_map_preference("cute_route")
        return

    url = _build_url(amap_key, stops)
    masked_url = mask_amap_key(url)
    try:
        with urlopen(url, timeout=30) as response:
            content = response.read()
            content_type = response.headers.get("Content-Type", "")
        if not content.startswith(b"\x89PNG") and "image" not in content_type:
            raise RuntimeError(f"AMap did not return an image: {content[:120]!r}")
        PNG_PATH.write_bytes(content)
        URL_PATH.write_text(masked_url, encoding="utf-8")
        write_json(
            METADATA_PATH,
            {
                "ok": True,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "stop_count": len(stops),
                "masked_url": masked_url,
                "coordinate_note": "EXIF GPS 为 WGS84；高德静态地图使用 GCJ-02，当前 MVP 可能存在偏移。",
                "output": str(PNG_PATH),
            },
        )
        append_call_log(
            CALL_LOG,
            {
                "time": datetime.now().isoformat(timespec="seconds"),
                "type": "static_map",
                "called_api": True,
                "ok": True,
                "masked_url": masked_url,
                "error": "",
            },
        )
        _update_album_map_preference("amap_static")
        print(f"api_calls=1")
        print(f"output={PNG_PATH}")
    except Exception as exc:
        write_json(
            METADATA_PATH,
            {
                "ok": False,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "stop_count": len(stops),
                "masked_url": masked_url,
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
        append_call_log(
            CALL_LOG,
            {
                "time": datetime.now().isoformat(timespec="seconds"),
                "type": "static_map",
                "called_api": True,
                "ok": False,
                "masked_url": masked_url,
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
        print(f"api_calls=1")
        print(f"static_map_error={type(exc).__name__}: {exc}")
        _fallback()
        _update_album_map_preference("cute_route")


if __name__ == "__main__":
    main()
