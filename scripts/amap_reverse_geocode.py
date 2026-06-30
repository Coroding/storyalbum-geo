from __future__ import annotations

import argparse
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import urlopen

from geo_album_utils import (
    CACHE_DIR,
    META_DIR,
    append_call_log,
    cache_key_for_coord,
    ensure_geo_dirs,
    get_amap_key,
    mask_amap_key,
    pick_stop_name,
    read_json,
    simplify_regeocode,
    write_json,
)


REGEOCODE_URL = "https://restapi.amap.com/v3/geocode/regeo"
CALL_LOG = CACHE_DIR / "amap_call_log.json"


def _request_regeocode(key: str, lat: float, lng: float) -> tuple[dict, str]:
    params = {
        "key": key,
        "location": f"{lng},{lat}",
        "extensions": "all",
        "radius": "1000",
        "roadlevel": "0",
        "output": "json",
    }
    url = f"{REGEOCODE_URL}?{urlencode(params, safe=',')}"
    with urlopen(url, timeout=20) as response:
        data = response.read().decode("utf-8")
    return __import__("json").loads(data), url


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument("--max-calls", type=int, default=50)
    args = parser.parse_args()

    ensure_geo_dirs()
    raw = read_json(META_DIR / "geo_stops_raw.json", default={"stops": []})
    stops = raw.get("stops", [])
    cache = read_json(CACHE_DIR / "regeocode_cache.json", default={})
    if not isinstance(cache, dict):
        cache = {}

    missing = []
    for stop in stops:
        coord = stop.get("centroid_wgs84") or {}
        if "lat" not in coord or "lng" not in coord:
            continue
        key = cache_key_for_coord(float(coord["lat"]), float(coord["lng"]))
        if args.force_refresh or key not in cache:
            missing.append((stop, key))

    planned = min(len(missing), max(args.max_calls, 0))
    if args.dry_run:
        print(f"stops={len(stops)}")
        print(f"cached={len(stops) - len(missing)}")
        print(f"planned_api_calls={planned}")
        print(f"max_calls={args.max_calls}")
        return

    amap_key = get_amap_key()
    calls = 0
    if not amap_key and missing:
        print("AMap key is missing; enrichment will use cache/fallback names only.")

    for stop, coord_key in missing:
        if calls >= args.max_calls:
            break
        coord = stop.get("centroid_wgs84") or {}
        if not amap_key:
            cache[coord_key] = {
                "ok": False,
                "error": "AMap key missing",
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
            continue
        try:
            raw_response, url = _request_regeocode(amap_key, float(coord["lat"]), float(coord["lng"]))
            calls += 1
            ok = raw_response.get("status") == "1"
            cache[coord_key] = {
                "ok": ok,
                "raw": raw_response if ok else {},
                "regeocode": simplify_regeocode(raw_response) if ok else {},
                "error": "" if ok else raw_response.get("info", "AMap request failed"),
                "infocode": raw_response.get("infocode", ""),
                "masked_url": mask_amap_key(url),
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
            append_call_log(
                CALL_LOG,
                {
                    "time": datetime.now().isoformat(timespec="seconds"),
                    "type": "reverse_geocode",
                    "called_api": True,
                    "coord_key": coord_key,
                    "ok": ok,
                    "masked_url": mask_amap_key(url),
                    "error": "" if ok else raw_response.get("info", "AMap request failed"),
                },
            )
        except Exception as exc:
            calls += 1
            cache[coord_key] = {
                "ok": False,
                "raw": {},
                "regeocode": {},
                "error": f"{type(exc).__name__}: {exc}",
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
            append_call_log(
                CALL_LOG,
                {
                    "time": datetime.now().isoformat(timespec="seconds"),
                    "type": "reverse_geocode",
                    "called_api": True,
                    "coord_key": coord_key,
                    "ok": False,
                    "masked_url": "",
                    "error": f"{type(exc).__name__}: {exc}",
                },
            )

    enriched_stops = []
    for stop in stops:
        new_stop = dict(stop)
        coord = stop.get("centroid_wgs84") or {}
        coord_key = cache_key_for_coord(float(coord["lat"]), float(coord["lng"])) if "lat" in coord and "lng" in coord else ""
        cached = cache.get(coord_key, {})
        regeocode = cached.get("regeocode") or {}
        new_stop["amap"] = {
            "coord_note": "EXIF GPS 为 WGS84；当前 MVP 未做 WGS84 到 GCJ-02 转换，地图和地址可能存在偏移。",
            "cache_key": coord_key,
            "ok": bool(cached.get("ok")),
            "formatted_address": regeocode.get("formatted_address", ""),
            "country": regeocode.get("country", ""),
            "province": regeocode.get("province", ""),
            "city": regeocode.get("city", ""),
            "district": regeocode.get("district", ""),
            "township": regeocode.get("township", ""),
            "neighborhood": regeocode.get("neighborhood", ""),
            "building": regeocode.get("building", ""),
            "adcode": regeocode.get("adcode", ""),
            "pois": regeocode.get("pois", []),
            "aois": regeocode.get("aois", []),
            "error": cached.get("error", ""),
        }
        new_stop["name"] = pick_stop_name({"pois": regeocode.get("pois", []), "aois": regeocode.get("aois", []), "addressComponent": regeocode, "formatted_address": regeocode.get("formatted_address", "")}, stop.get("name", "地点"))
        if new_stop["amap"]["ok"]:
            new_stop["data_source"] = "EXIF GPS + AMap reverse geocode"
        enriched_stops.append(new_stop)

    output = {
        "type": "geo_stops_enriched",
        "api": "AMap reverse geocode",
        "api_call_count_this_run": calls,
        "used_cache": any(cache_key_for_coord(float((s.get("centroid_wgs84") or {})["lat"]), float((s.get("centroid_wgs84") or {})["lng"])) in cache for s in stops if (s.get("centroid_wgs84") or {}).get("lat") is not None),
        "coordinate_note": "EXIF GPS 为 WGS84；高德使用 GCJ-02，当前 MVP 可能存在偏移。",
        "stops": enriched_stops,
    }
    write_json(CACHE_DIR / "regeocode_cache.json", cache)
    write_json(META_DIR / "geo_stops_enriched.json", output)
    print(f"api_calls={calls}")
    print(f"cache={CACHE_DIR / 'regeocode_cache.json'}")
    print(f"output={META_DIR / 'geo_stops_enriched.json'}")


if __name__ == "__main__":
    main()
