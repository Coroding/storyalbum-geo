from __future__ import annotations

import shutil

from geo_album_utils import (
    CACHE_DIR,
    DEMO_DATA_DIR,
    MAP_AMAP_DIR,
    MAP_STYLED_DIR,
    META_DIR,
    PROJECT_ROOT,
    SELECTED_DIR,
    count_api_calls,
    ensure_geo_dirs,
    read_json,
    relative_to_demo,
    write_json,
)


def _load_stops() -> list[dict]:
    enriched = read_json(META_DIR / "geo_stops_enriched.json", default=None)
    if enriched:
        return enriched.get("stops", [])
    raw = read_json(META_DIR / "geo_stops_raw.json", default={"stops": []})
    return raw.get("stops", [])


def _copy_selected(photo: dict, prefix: str = "") -> str:
    source = PROJECT_ROOT / photo["relative_path"]
    if not source.exists():
        return relative_to_demo(source)
    target_name = f"{prefix}{source.name}" if prefix else source.name
    target = SELECTED_DIR / target_name
    if not target.exists():
        shutil.copy2(source, target)
    return relative_to_demo(target)


def main() -> None:
    ensure_geo_dirs()
    manifest = read_json(META_DIR / "photo_manifest.json", default=[])
    stops = _load_stops()
    gps_photos = [photo for photo in manifest if photo.get("has_gps")]
    cover_photo = gps_photos[0] if gps_photos else (manifest[0] if manifest else None)
    cover_path = _copy_selected(cover_photo, "cover_") if cover_photo else ""

    amap_png = MAP_AMAP_DIR / "geo_route_amap.png"
    fallback_svg = MAP_STYLED_DIR / "cute_geo_route.svg"
    preferred = "amap_static" if amap_png.exists() else "cute_route"
    all_photos = []
    for index, photo in enumerate(manifest, start=1):
        item = dict(photo)
        item["src"] = _copy_selected(photo, f"{index:02d}_") if photo.get("relative_path") else ""
        all_photos.append(item)

    album_stops = []
    for stop in stops:
        amap = stop.get("amap") or {}
        photos = []
        for photo_index, photo in enumerate(stop.get("photos", [])[:6], start=1):
            photo_item = dict(photo)
            photo_item["src"] = _copy_selected(photo, f"stop{int(stop.get('order', 0)):02d}_{photo_index:02d}_")
            photos.append(photo_item)
        album_stops.append(
            {
                "order": stop.get("order"),
                "name": stop.get("name", ""),
                "formattedAddress": amap.get("formatted_address", ""),
                "province": amap.get("province", ""),
                "city": amap.get("city", ""),
                "district": amap.get("district", ""),
                "township": amap.get("township", ""),
                "pois": amap.get("pois", []),
                "aois": amap.get("aois", []),
                "photos": photos,
                "caption": stop.get("caption", ""),
                "dataSource": stop.get("data_source", "EXIF GPS"),
                "coordinate": stop.get("centroid_wgs84", {}),
                "note": amap.get("coord_note", "EXIF GPS 为 WGS84；当前 MVP 可能存在高德坐标偏移。"),
                "error": amap.get("error", ""),
            }
        )

    api_call_count = count_api_calls(CACHE_DIR / "amap_call_log.json")
    album = {
        "title": "我的旅行路线回忆",
        "subtitle": "基于照片地理信息自动生成",
        "type": "geo_memory_album",
        "cover": cover_path,
        "map": {
            "preferred": preferred,
            "amapStatic": relative_to_demo(amap_png),
            "fallback": relative_to_demo(fallback_svg),
            "fallbackPng": relative_to_demo(MAP_STYLED_DIR / "cute_geo_route.png"),
            "note": "地图结果已缓存，本页不在前端请求高德 API",
        },
        "stops": album_stops,
        "photos": all_photos,
        "stats": {
            "photoCount": len(manifest),
            "gpsPhotoCount": len(gps_photos),
            "nonGpsPhotoCount": len(manifest) - len(gps_photos),
            "stopCount": len(stops),
            "apiCallCount": api_call_count,
            "reverseGeocodeCallCount": sum(1 for item in read_json(CACHE_DIR / "amap_call_log.json", default=[]) if item.get("type") == "reverse_geocode" and item.get("called_api")),
            "staticMapCallCount": sum(1 for item in read_json(CACHE_DIR / "amap_call_log.json", default=[]) if item.get("type") == "static_map" and item.get("called_api")),
            "hasAmapReverseGeocode": any((stop.get("amap") or {}).get("ok") for stop in stops),
            "hasAmapStaticMap": amap_png.exists(),
            "usedFallbackMap": not amap_png.exists(),
        },
        "notes": [
            "照片 EXIF GPS 通常为 WGS84；高德地图使用 GCJ-02，当前 MVP 可能存在坐标偏移。",
            "所有高德 API 请求都在 Python 脚本中完成；前端只读取本地 JSON 和缓存图片。",
        ],
    }
    write_json(DEMO_DATA_DIR / "geo_album.json", album)
    (DEMO_DATA_DIR / "geo_album.js").write_text(
        "window.STORYALBUM_GEO_DATA = " + __import__("json").dumps(album, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    print(f"output={DEMO_DATA_DIR / 'geo_album.json'}")
    print(f"photo_count={len(manifest)}")
    print(f"gps_photo_count={len(gps_photos)}")
    print(f"stop_count={len(stops)}")


if __name__ == "__main__":
    main()
