from __future__ import annotations

import csv
import json
import math
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GEO_ROOT = PROJECT_ROOT / "assets" / "geo_album"
SOURCE_DIR = GEO_ROOT / "source_photos" / "original"
SELECTED_DIR = GEO_ROOT / "source_photos" / "selected"
MAP_AMAP_DIR = GEO_ROOT / "maps" / "amap"
MAP_STYLED_DIR = GEO_ROOT / "maps" / "styled"
META_DIR = GEO_ROOT / "meta"
CACHE_DIR = GEO_ROOT / "cache"
DEMO_DATA_DIR = PROJECT_ROOT / "demo-site" / "data"
OUTPUT_DIR = PROJECT_ROOT / "output" / "geo_album"
PREVIEW_DIR = PROJECT_ROOT / "_preview" / "geo_album"
DOC_PRODUCT_DIR = PROJECT_ROOT / "docs" / "product"
DOC_SHOWCASE_DIR = PROJECT_ROOT / "docs" / "showcase"
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".webp"}


def ensure_geo_dirs() -> None:
    for path in [
        SOURCE_DIR,
        SELECTED_DIR,
        MAP_AMAP_DIR,
        MAP_STYLED_DIR,
        META_DIR,
        CACHE_DIR,
        DEMO_DATA_DIR,
        OUTPUT_DIR,
        PREVIEW_DIR,
        DOC_PRODUCT_DIR,
        DOC_SHOWCASE_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def load_env_local() -> dict[str, str]:
    values: dict[str, str] = {}
    env_path = PROJECT_ROOT / ".env.local"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def get_amap_key() -> str:
    return os.environ.get("AMAP_WEB_SERVICE_KEY") or load_env_local().get("AMAP_WEB_SERVICE_KEY", "")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def posix_rel(path: Path, base: Path = PROJECT_ROOT) -> str:
    return path.resolve().relative_to(base.resolve()).as_posix()


def relative_to_demo(path: Path, project_root: Path = PROJECT_ROOT) -> str:
    demo_dir = project_root / "demo-site"
    return os.path.relpath(path, demo_dir).replace("\\", "/")


def parse_photo_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y%m%d_%H%M%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    match = re.search(r"(\d{8})[_-]?(\d{6})", value)
    if match:
        try:
            return datetime.strptime("".join(match.groups()), "%Y%m%d%H%M%S")
        except ValueError:
            return None
    return None


def photo_sort_key(photo: dict[str, Any]) -> tuple[str, str]:
    dt = parse_photo_datetime(photo.get("datetime_original"))
    if dt:
        return (dt.isoformat(), photo.get("filename", ""))
    fallback = photo.get("sort_time") or photo.get("filename", "")
    return (str(fallback), photo.get("filename", ""))


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _centroid(photos: list[dict[str, Any]]) -> dict[str, float]:
    lat = sum(float(p["gps_lat_wgs84"]) for p in photos) / len(photos)
    lng = sum(float(p["gps_lng_wgs84"]) for p in photos) / len(photos)
    return {"lat": round(lat, 7), "lng": round(lng, 7)}


def _caption(index: int, total: int) -> str:
    if index == 0:
        return "第一站：旅程开始"
    if index == total - 1:
        return "最后一站：路线收尾"
    return "中间站：沿途停留"


def cluster_photo_records(photos: list[dict[str, Any]], threshold_m: int = 200) -> list[dict[str, Any]]:
    gps_photos = [
        photo
        for photo in photos
        if photo.get("has_gps") and photo.get("gps_lat_wgs84") not in ("", None) and photo.get("gps_lng_wgs84") not in ("", None)
    ]
    gps_photos.sort(key=photo_sort_key)
    if not gps_photos:
        return []

    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for photo in gps_photos:
        if not current:
            current = [photo]
            continue
        center = _centroid(current)
        distance = haversine_m(center["lat"], center["lng"], float(photo["gps_lat_wgs84"]), float(photo["gps_lng_wgs84"]))
        if distance <= threshold_m:
            current.append(photo)
        else:
            groups.append(current)
            current = [photo]
    if current:
        groups.append(current)

    stops: list[dict[str, Any]] = []
    for index, group in enumerate(groups):
        centroid = _centroid(group)
        ordered_group = sorted(group, key=photo_sort_key)
        start_time = ordered_group[0].get("datetime_original") or ordered_group[0].get("sort_time") or ""
        end_time = ordered_group[-1].get("datetime_original") or ordered_group[-1].get("sort_time") or ""
        representative = ordered_group[:6]
        stops.append(
            {
                "order": index + 1,
                "name": f"地点 {index + 1:02d}",
                "centroid_wgs84": centroid,
                "photos": [
                    {
                        "filename": p.get("filename"),
                        "relative_path": p.get("relative_path"),
                        "datetime_original": p.get("datetime_original"),
                        "width": p.get("width"),
                        "height": p.get("height"),
                    }
                    for p in representative
                ],
                "photo_count": len(group),
                "start_time": start_time,
                "end_time": end_time,
                "caption": _caption(index, len(groups)),
                "data_source": "EXIF GPS",
            }
        )
    return stops


def mask_amap_key(url: str) -> str:
    parts = urlsplit(url)
    query = [(key, "***" if key.lower() == "key" else value) for key, value in parse_qsl(parts.query, keep_blank_values=True)]
    masked_query = urlencode(query, doseq=True, safe="*,;:|,")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, masked_query.replace("%2A%2A%2A", "***"), parts.fragment))


def cache_key_for_coord(lat: float, lng: float) -> str:
    return f"{lat:.6f},{lng:.6f}"


def pick_stop_name(regeocode: dict[str, Any] | None, fallback: str) -> str:
    if not regeocode:
        return fallback
    pois = regeocode.get("pois") or []
    if pois and pois[0].get("name"):
        return str(pois[0]["name"])
    aois = regeocode.get("aois") or []
    if aois and aois[0].get("name"):
        return str(aois[0]["name"])
    component = regeocode.get("addressComponent") or {}
    for key in ("township", "district"):
        value = component.get(key)
        if value:
            return str(value)
    address = regeocode.get("formatted_address")
    if address:
        text = str(address)
        return text[-14:] if len(text) > 14 else text
    return fallback


def simplify_regeocode(raw: dict[str, Any]) -> dict[str, Any]:
    regeocode = raw.get("regeocode") or raw
    component = regeocode.get("addressComponent") or {}
    pois = [
        {
            "name": poi.get("name", ""),
            "type": poi.get("type", ""),
            "distance": poi.get("distance", ""),
            "direction": poi.get("direction", ""),
        }
        for poi in (regeocode.get("pois") or [])[:3]
    ]
    aois = [
        {
            "name": aoi.get("name", ""),
            "type": aoi.get("type", ""),
            "distance": aoi.get("distance", ""),
        }
        for aoi in (regeocode.get("aois") or [])[:3]
    ]
    return {
        "formatted_address": regeocode.get("formatted_address", ""),
        "country": component.get("country", ""),
        "province": component.get("province", ""),
        "city": component.get("city", ""),
        "district": component.get("district", ""),
        "township": component.get("township", ""),
        "neighborhood": (component.get("neighborhood") or {}).get("name", "") if isinstance(component.get("neighborhood"), dict) else "",
        "building": (component.get("building") or {}).get("name", "") if isinstance(component.get("building"), dict) else "",
        "adcode": component.get("adcode", ""),
        "pois": pois,
        "aois": aois,
    }


def count_api_calls(log_path: Path) -> int:
    entries = read_json(log_path, default=[])
    if not isinstance(entries, list):
        return 0
    return sum(1 for item in entries if item.get("called_api"))


def append_call_log(path: Path, entry: dict[str, Any]) -> None:
    log = read_json(path, default=[])
    if not isinstance(log, list):
        log = []
    log.append(entry)
    write_json(path, log)
