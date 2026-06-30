from __future__ import annotations

from math import cos, radians, sin
from typing import Any


VIEWBOX_WIDTH = 1000
VIEWBOX_HEIGHT = 680
PADDING_RATIO = 0.1
LABEL_LIMIT = 8
KEY_LABEL_TERMS = ("丽江", "泸沽湖", "里格", "大落水", "观音峡", "情人滩")


def _to_float(value: Any) -> float | None:
    if value in ("", None):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_coord_from_photos(stop: dict[str, Any]) -> tuple[float, float] | None:
    for photo in stop.get("photos") or []:
        lat = _to_float(photo.get("lat") or photo.get("gps_lat_wgs84") or photo.get("gps_lat"))
        lng = _to_float(photo.get("lng") or photo.get("gps_lng_wgs84") or photo.get("gps_lng"))
        if lat is not None and lng is not None:
            return lat, lng
    return None


def _coord_from_cached_amap(stop: dict[str, Any]) -> tuple[float, float] | None:
    amap = stop.get("amap") or {}
    raw = amap.get("location") or amap.get("coord") or amap.get("marker")
    if isinstance(raw, dict):
        lat = _to_float(raw.get("lat"))
        lng = _to_float(raw.get("lng"))
        if lat is not None and lng is not None:
            return lat, lng
    if isinstance(raw, str) and "," in raw:
        lng_text, lat_text = raw.split(",", 1)
        lat = _to_float(lat_text)
        lng = _to_float(lng_text)
        if lat is not None and lng is not None:
            return lat, lng
    return None


def resolve_stop_coordinate(stop: dict[str, Any]) -> tuple[float | None, float | None, str]:
    direct_lat = _to_float(stop.get("lat"))
    direct_lng = _to_float(stop.get("lng"))
    if direct_lat is not None and direct_lng is not None:
        return direct_lat, direct_lng, "exact"

    centroid = stop.get("centroid_wgs84") or {}
    lat = _to_float(centroid.get("lat"))
    lng = _to_float(centroid.get("lng"))
    if lat is not None and lng is not None:
        return lat, lng, "exact"

    photo_coord = _first_coord_from_photos(stop)
    if photo_coord:
        return photo_coord[0], photo_coord[1], "exact"

    cached_coord = _coord_from_cached_amap(stop)
    if cached_coord:
        return cached_coord[0], cached_coord[1], "cached"

    manual = stop.get("manual_fallback") or stop.get("fallback_coord") or {}
    manual_lat = _to_float(manual.get("lat"))
    manual_lng = _to_float(manual.get("lng"))
    if manual_lat is not None and manual_lng is not None:
        return manual_lat, manual_lng, "estimated"

    return None, None, "fallback"


def _fallback_points(stops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    usable_width = VIEWBOX_WIDTH * (1 - PADDING_RATIO * 2)
    usable_height = VIEWBOX_HEIGHT * (1 - PADDING_RATIO * 2)
    left = VIEWBOX_WIDTH * PADDING_RATIO
    top = VIEWBOX_HEIGHT * PADDING_RATIO
    count = max(len(stops), 1)
    points = []
    for index, stop in enumerate(stops):
        t = index / max(count - 1, 1)
        x = left + usable_width * (0.12 + 0.76 * t)
        y = top + usable_height * (0.52 + 0.28 * sin(t * 3.14159 * 1.5))
        points.append(_make_point(stop, index, x, y, None, None, "fallback", 0.12 + 0.76 * t, y / VIEWBOX_HEIGHT))
    return points


def _make_point(
    stop: dict[str, Any],
    index: int,
    x: float,
    y: float,
    lat: float | None,
    lng: float | None,
    confidence: str,
    normalized_x: float,
    normalized_y: float,
) -> dict[str, Any]:
    photos = stop.get("photos") or []
    order = int(stop.get("order") or index + 1)
    name = str(stop.get("name") or f"地点 {order:02d}")
    return {
        "order": order,
        "name": name,
        "time": stop.get("start_time") or stop.get("datetime_original") or "",
        "photo_count": int(stop.get("photo_count") or len(photos)),
        "caption": stop.get("caption") or "",
        "poi": ((stop.get("pois") or [{}])[0].get("name") if stop.get("pois") else ""),
        "lat": lat,
        "lng": lng,
        "normalized_x": round(normalized_x, 4),
        "normalized_y": round(normalized_y, 4),
        "x": round(x, 2),
        "y": round(y, 2),
        "confidence": confidence,
        "show_label": False,
        "label_position": "right",
    }


def _choose_label_position(point: dict[str, Any], index: int, total: int) -> str:
    if index == 0:
        return "right-top" if point["x"] < VIEWBOX_WIDTH * 0.55 else "left-top"
    if index == total - 1:
        return "left-top" if point["x"] > VIEWBOX_WIDTH * 0.55 else "right-top"
    if point["x"] < VIEWBOX_WIDTH * 0.38:
        return "right"
    if point["x"] > VIEWBOX_WIDTH * 0.62:
        return "left"
    return "bottom" if point["y"] < VIEWBOX_HEIGHT * 0.5 else "top"


def _apply_visual_jitter(points: list[dict[str, Any]]) -> None:
    for index, point in enumerate(points):
        close_before = sum(
            1
            for previous in points[:index]
            if abs(previous["x"] - point["x"]) < 28 and abs(previous["y"] - point["y"]) < 28
        )
        if close_before:
            point["x"] = round(point["x"] + min(22, close_before * 9), 2)
            point["y"] = round(point["y"] + min(18, close_before * 7), 2)


def _apply_label_rules(points: list[dict[str, Any]]) -> None:
    if not points:
        return
    selected = {0, len(points) - 1}
    cluster_counts: dict[tuple[int, int], int] = {}

    def cluster_key(point: dict[str, Any]) -> tuple[int, int]:
        return int(float(point["x"]) // 180), int(float(point["y"]) // 140)

    for index in selected:
        key = cluster_key(points[index])
        cluster_counts[key] = cluster_counts.get(key, 0) + 1

    scored = []
    for index, point in enumerate(points):
        score = point.get("photo_count", 0)
        if any(term in point["name"] for term in KEY_LABEL_TERMS):
            score += 100
        if point.get("time"):
            score += 2
        scored.append((score, -abs(index - len(points) / 2), index))

    for _score, _middle_bias, index in sorted(scored, reverse=True):
        if len(selected) >= min(LABEL_LIMIT, len(points)):
            break
        key = cluster_key(points[index])
        if cluster_counts.get(key, 0) >= 2:
            continue
        selected.add(index)
        cluster_counts[key] = cluster_counts.get(key, 0) + 1

    for index, point in enumerate(points):
        point["show_label"] = index in selected
        point["label_position"] = _choose_label_position(point, index, len(points))


def _turnaround_index(points: list[dict[str, Any]]) -> int:
    if len(points) < 2:
        return 0
    start = points[0]
    distances = [
        (float(point["x"]) - float(start["x"])) ** 2 + (float(point["y"]) - float(start["y"])) ** 2
        for point in points
    ]
    return max(range(len(points)), key=lambda index: distances[index])


def project_route_stops(stops: list[dict[str, Any]], width: int = VIEWBOX_WIDTH, height: int = VIEWBOX_HEIGHT) -> dict[str, Any]:
    if width != VIEWBOX_WIDTH or height != VIEWBOX_HEIGHT:
        raise ValueError("This MVP projection uses the fixed 1000x680 album map viewBox.")

    ordered = sorted(stops, key=lambda item: int(item.get("order") or 9999))
    resolved = []
    for index, stop in enumerate(ordered):
        lat, lng, confidence = resolve_stop_coordinate(stop)
        resolved.append((index, stop, lat, lng, confidence))

    coordinate_items = [(idx, stop, lat, lng, confidence) for idx, stop, lat, lng, confidence in resolved if lat is not None and lng is not None]
    mode = "coordinate-based" if len(coordinate_items) >= 2 else "order-based fallback"

    if mode == "order-based fallback":
        points = _fallback_points(ordered)
        bbox = {"min_lng": None, "max_lng": None, "min_lat": None, "max_lat": None}
        aspect_ratio = round(width / height, 4)
    else:
        lats = [float(item[2]) for item in coordinate_items]
        lngs = [float(item[3]) for item in coordinate_items]
        mid_lat = sum(lats) / len(lats)
        cos_mid = max(cos(radians(mid_lat)), 0.2)
        xs = [lng * cos_mid for lng in lngs]
        ys = lats
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(max_x - min_x, 1e-7)
        span_y = max(max_y - min_y, 1e-7)
        box_ratio = span_x / span_y
        canvas_ratio = width / height
        pad_x = width * PADDING_RATIO
        pad_y = height * PADDING_RATIO
        usable_w = width - pad_x * 2
        usable_h = height - pad_y * 2
        if box_ratio > canvas_ratio:
            scale = usable_w / span_x
            drawn_w = usable_w
            drawn_h = span_y * scale
        else:
            scale = usable_h / span_y
            drawn_h = usable_h
            drawn_w = span_x * scale
        origin_x = (width - drawn_w) / 2
        origin_y = (height - drawn_h) / 2

        points = []
        coord_by_index = {idx: (lat, lng, confidence) for idx, stop, lat, lng, confidence in coordinate_items}
        for index, stop in enumerate(ordered):
            lat, lng, confidence = coord_by_index.get(index, (None, None, "fallback"))
            if lat is None or lng is None:
                # Missing coordinates stay on route order but are clearly marked estimated.
                t = index / max(len(ordered) - 1, 1)
                x = origin_x + drawn_w * t
                y = origin_y + drawn_h * (0.5 + 0.16 * sin(t * 3.14159))
                points.append(_make_point(stop, index, x, y, None, None, "fallback", t, y / height))
                continue
            normalized_x = ((lng * cos_mid) - min_x) / span_x
            normalized_y = 1 - ((lat - min_y) / span_y)
            x = origin_x + normalized_x * drawn_w
            y = origin_y + normalized_y * drawn_h
            points.append(_make_point(stop, index, x, y, lat, lng, confidence, normalized_x, normalized_y))

        bbox = {
            "min_lng": min(lngs),
            "max_lng": max(lngs),
            "min_lat": min(lats),
            "max_lat": max(lats),
        }
        aspect_ratio = round(box_ratio, 4)

    _apply_visual_jitter(points)
    _apply_label_rules(points)
    source_counts = {
        "exact": sum(1 for point in points if point["confidence"] == "exact"),
        "cached": sum(1 for point in points if point["confidence"] == "cached"),
        "estimated": sum(1 for point in points if point["confidence"] == "estimated"),
        "fallback": sum(1 for point in points if point["confidence"] == "fallback"),
    }
    label_count = sum(1 for point in points if point["show_label"])
    inspection = "coordinate-based" if source_counts["exact"] else ("cached-based" if source_counts["cached"] else "fallback")
    turnaround_index = _turnaround_index(points)
    return {
        "mode": mode,
        "inspection": inspection,
        "turnaround_index": turnaround_index,
        "view_box": {"width": width, "height": height},
        "bbox": bbox,
        "aspect_ratio": aspect_ratio,
        "source_counts": source_counts,
        "label_count": label_count,
        "hidden_label_count": max(0, len(points) - label_count),
        "points": points,
    }
