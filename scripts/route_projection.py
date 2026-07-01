from __future__ import annotations

import math
from html import escape
from typing import Any


VIEWBOX_WIDTH = 1000
VIEWBOX_HEIGHT = 680
LABEL_LIMIT = 6
MIN_SPAN_X = 0.001
MIN_SPAN_Y = 0.001
KEY_LABEL_TERMS = ("丽江", "泸沽湖", "里格", "大落水", "观音峡", "情人滩")
CANDIDATE_LABEL_POSITIONS = ("top", "top-right", "right", "bottom-right", "bottom", "bottom-left", "left", "top-left")


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


def _mercator_y(lat: float) -> float:
    clamped = max(-85.0, min(85.0, lat))
    return math.log(math.tan(math.pi / 4 + math.radians(clamped) / 2))


def _map_area(width: int, height: int, padding: dict[str, Any] | None = None) -> dict[str, float]:
    padding = padding or {}
    left = _to_float(padding.get("left")) or 72.0
    right = _to_float(padding.get("right")) or 72.0
    top = _to_float(padding.get("top")) or 80.0
    bottom = _to_float(padding.get("bottom")) or 160.0
    return {"left": left, "right": width - right, "top": top, "bottom": height - bottom}


def _order_fallback_points(ordered: list[dict[str, Any]], map_area: dict[str, float]) -> list[dict[str, Any]]:
    count = max(len(ordered), 1)
    drawable_w = map_area["right"] - map_area["left"]
    drawable_h = map_area["bottom"] - map_area["top"]
    points = []
    for index, stop in enumerate(ordered):
        t = index / max(count - 1, 1)
        x = map_area["left"] + drawable_w * (0.08 + 0.84 * t)
        y = map_area["top"] + drawable_h * (0.52 + 0.22 * math.sin(t * math.pi * 1.35))
        points.append(_make_point(stop, index, x, y, x, y, None, None, "fallback"))
    return points


def _make_point(
    stop: dict[str, Any],
    index: int,
    x: float,
    y: float,
    raw_x: float,
    raw_y: float,
    lat: float | None,
    lng: float | None,
    confidence: str,
) -> dict[str, Any]:
    photos = stop.get("photos") or []
    order = int(stop.get("order") or index + 1)
    return {
        "order": order,
        "name": str(stop.get("name") or f"地点 {order:02d}"),
        "caption": str(stop.get("caption") or ""),
        "time": stop.get("start_time") or stop.get("datetime_original") or "",
        "photo_count": int(stop.get("photo_count") or len(photos)),
        "dataSource": stop.get("dataSource") or stop.get("data_source") or "",
        "lat": lat,
        "lng": lng,
        "x": round(x, 2),
        "y": round(y, 2),
        "rawX": round(raw_x, 6),
        "rawY": round(raw_y, 6),
        "labelX": None,
        "labelY": None,
        "labelAnchor": "hidden",
        "labelConnector": None,
        "labelWidth": 150,
        "labelHeight": 38,
        "labelOffset": stop.get("labelOffset") or {},
        "hideLabel": bool(stop.get("hideLabel")),
        "show_label": False,
        "isClustered": False,
        "clusterId": "",
        "confidence": confidence,
    }


def _expand_span(min_value: float, max_value: float, min_span: float) -> tuple[float, float]:
    span = max_value - min_value
    if span >= min_span:
        return min_value, max_value
    center = (min_value + max_value) / 2
    return center - min_span / 2, center + min_span / 2


def _project_coordinate_points(
    ordered: list[dict[str, Any]],
    resolved: list[tuple[int, dict[str, Any], float | None, float | None, str]],
    width: int,
    height: int,
    map_area: dict[str, float],
    warnings: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    coordinate_items = [(idx, stop, lat, lng, source) for idx, stop, lat, lng, source in resolved if lat is not None and lng is not None]
    if len(coordinate_items) < 2:
        warnings.append("not_enough_coordinates: using order-based fallback")
        points = _order_fallback_points(ordered, map_area)
        return points, {"minX": None, "maxX": None, "minY": None, "maxY": None}, "order-based fallback"

    mercator = [
        (idx, stop, math.radians(float(lng)), _mercator_y(float(lat)), float(lat), float(lng), source)
        for idx, stop, lat, lng, source in coordinate_items
    ]
    xs = [item[2] for item in mercator]
    ys = [item[3] for item in mercator]
    min_x, max_x = _expand_span(min(xs), max(xs), MIN_SPAN_X)
    min_y, max_y = _expand_span(min(ys), max(ys), MIN_SPAN_Y)
    span_x = max_x - min_x
    span_y = max_y - min_y
    if span_x <= MIN_SPAN_X or span_y <= MIN_SPAN_Y:
        warnings.append("small_bbox_span: min span applied")

    drawable_w = map_area["right"] - map_area["left"]
    drawable_h = map_area["bottom"] - map_area["top"]
    raw_ratio = span_x / span_y
    draw_ratio = drawable_w / drawable_h
    if raw_ratio > draw_ratio:
        scale = drawable_w / span_x
        fitted_w = drawable_w
        fitted_h = span_y * scale
    else:
        scale = drawable_h / span_y
        fitted_h = drawable_h
        fitted_w = span_x * scale
    origin_x = map_area["left"] + (drawable_w - fitted_w) / 2
    origin_y = map_area["top"] + (drawable_h - fitted_h) / 2

    projected_by_index = {}
    for idx, stop, merc_x, merc_y, lat, lng, source in mercator:
        x = origin_x + (merc_x - min_x) * scale
        y = origin_y + (max_y - merc_y) * scale
        projected_by_index[idx] = (x, y, merc_x, merc_y, lat, lng, source)

    points = []
    for index, stop in enumerate(ordered):
        if index in projected_by_index:
            x, y, raw_x, raw_y, lat, lng, source = projected_by_index[index]
            points.append(_make_point(stop, index, x, y, raw_x, raw_y, lat, lng, source))
        else:
            warnings.append(f"missing_coordinate_stop_{stop.get('order')}: kept in timeline/fallback position")
            t = index / max(len(ordered) - 1, 1)
            x = map_area["left"] + drawable_w * t
            y = map_area["bottom"]
            points.append(_make_point(stop, index, x, y, x, y, None, None, "fallback"))

    bbox = {
        "minX": min_x,
        "maxX": max_x,
        "minY": min_y,
        "maxY": max_y,
        "minLng": min(item[5] for item in mercator),
        "maxLng": max(item[5] for item in mercator),
        "minLat": min(item[4] for item in mercator),
        "maxLat": max(item[4] for item in mercator),
    }
    return points, bbox, "coordinate-based"


def _distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    return math.hypot(float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"]))


def _disperse_close_points(points: list[dict[str, Any]], map_area: dict[str, float]) -> None:
    visited: set[int] = set()
    cluster_id = 1
    for index, point in enumerate(points):
        if index in visited:
            continue
        group = [idx for idx, other in enumerate(points) if idx not in visited and _distance(point, other) < 28]
        if len(group) <= 1:
            visited.add(index)
            continue
        center_x = sum(float(points[idx]["x"]) for idx in group) / len(group)
        center_y = sum(float(points[idx]["y"]) for idx in group) / len(group)
        radius = min(28, 18 + len(group) * 2)
        for offset, idx in enumerate(group):
            angle = (math.tau / len(group)) * offset - math.pi / 2
            if offset == 0:
                x = center_x
                y = center_y
            else:
                x = center_x + math.cos(angle) * radius
                y = center_y + math.sin(angle) * radius
            points[idx]["x"] = round(max(map_area["left"], min(map_area["right"], x)), 2)
            points[idx]["y"] = round(max(map_area["top"], min(map_area["bottom"], y)), 2)
            points[idx]["isClustered"] = True
            points[idx]["clusterId"] = f"cluster-{cluster_id}"
            visited.add(idx)
        cluster_id += 1


def _select_label_indexes(points: list[dict[str, Any]], limit: int = LABEL_LIMIT) -> set[int]:
    if not points:
        return set()
    selected = {0, len(points) - 1}
    scored = []
    for index, point in enumerate(points):
        if point.get("hideLabel"):
            continue
        score = point.get("photo_count", 0)
        if any(term in point["name"] for term in KEY_LABEL_TERMS):
            score += 100
        if index in selected:
            score += 1000
        scored.append((score, -index, index))
    for _score, _order_bias, index in sorted(scored, reverse=True):
        if len(selected) >= min(limit, len(points)):
            break
        selected.add(index)
    return selected


def _label_text_lines(point: dict[str, Any]) -> tuple[str, str]:
    name = str(point["name"])
    short_name = name[:10] + ("…" if len(name) > 10 else "")
    caption = str(point.get("caption") or "")
    caption = caption.replace("中间站：", "").replace("第一站：", "").replace("最后一站：", "")
    short_caption = caption[:12]
    return short_name, short_caption


def _candidate_label_boxes(point: dict[str, Any], map_area: dict[str, float]) -> list[dict[str, Any]]:
    width = 150
    line_1, line_2 = _label_text_lines(point)
    height = 46 if line_2 else 34
    x = float(point["x"])
    y = float(point["y"])
    gap = 16
    offsets = {
        "top": (-width / 2, -height - gap),
        "top-right": (gap, -height - gap),
        "right": (gap, -height / 2),
        "bottom-right": (gap, gap),
        "bottom": (-width / 2, gap),
        "bottom-left": (-width - gap, gap),
        "left": (-width - gap, -height / 2),
        "top-left": (-width - gap, -height - gap),
    }
    boxes = []
    for anchor, (dx, dy) in offsets.items():
        lx = max(map_area["left"], min(map_area["right"] - width, x + dx))
        ly = max(map_area["top"], min(map_area["bottom"] - height, y + dy))
        boxes.append({"anchor": anchor, "x": lx, "y": ly, "w": width, "h": height, "line1": line_1, "line2": line_2})
    return boxes


def _rect_intersection_area(a: dict[str, float], b: dict[str, float]) -> float:
    left = max(a["x"], b["x"])
    top = max(a["y"], b["y"])
    right = min(a["x"] + a["w"], b["x"] + b["w"])
    bottom = min(a["y"] + a["h"], b["y"] + b["h"])
    if right <= left or bottom <= top:
        return 0
    return (right - left) * (bottom - top)


def _place_labels(points: list[dict[str, Any]], map_area: dict[str, float], warnings: list[str]) -> None:
    label_indexes = _select_label_indexes(points)
    placed: list[dict[str, float]] = []
    marker_boxes = [{"x": float(point["x"]) - 18, "y": float(point["y"]) - 18, "w": 36, "h": 36} for point in points]
    for index, point in enumerate(points):
        if index not in label_indexes:
            continue
        best_box = None
        best_score = float("inf")
        for box in _candidate_label_boxes(point, map_area):
            score = 0.0
            for placed_box in placed:
                score += _rect_intersection_area(box, placed_box) * 3
            for marker_box in marker_boxes:
                score += _rect_intersection_area(box, marker_box)
            if score < best_score:
                best_score = score
                best_box = box
        if best_box is None:
            continue
        if best_score > 0 and index not in {0, len(points) - 1}:
            warnings.append(f"label_hidden_due_collision_stop_{point['order']}")
            continue
        if best_score > 0:
            warnings.append(f"label_collision_resolved_with_min_overlap_stop_{point['order']}")
        label_offset = point.get("labelOffset") or {}
        offset_x = _to_float(label_offset.get("x")) if isinstance(label_offset, dict) else 0
        offset_y = _to_float(label_offset.get("y")) if isinstance(label_offset, dict) else 0
        offset_x = offset_x or 0
        offset_y = offset_y or 0
        label_x = max(map_area["left"], min(map_area["right"] - best_box["w"], best_box["x"] + offset_x))
        label_y = max(map_area["top"], min(map_area["bottom"] - best_box["h"], best_box["y"] + offset_y))
        point["show_label"] = True
        point["labelX"] = round(label_x, 2)
        point["labelY"] = round(label_y, 2)
        point["labelWidth"] = best_box["w"]
        point["labelHeight"] = best_box["h"]
        point["labelAnchor"] = best_box["anchor"]
        point["labelLine1"] = best_box["line1"]
        point["labelLine2"] = best_box["line2"]
        point["labelConnector"] = {
            "x1": round(float(point["x"]), 2),
            "y1": round(float(point["y"]), 2),
            "x2": round(label_x + best_box["w"] / 2, 2),
            "y2": round(label_y + best_box["h"] / 2, 2),
        }
        placed.append(best_box)


def _route_path(points: list[dict[str, Any]]) -> str:
    if not points:
        return ""
    ordered = sorted(points, key=lambda point: int(point["order"]))
    if len(ordered) == 1:
        return f"M {ordered[0]['x']} {ordered[0]['y']}"
    if len(ordered) == 2:
        return f"M {ordered[0]['x']} {ordered[0]['y']} L {ordered[1]['x']} {ordered[1]['y']}"
    commands = [f"M {ordered[0]['x']:.1f} {ordered[0]['y']:.1f}"]
    for index in range(1, len(ordered)):
        prev = ordered[index - 1]
        current = ordered[index]
        cx = (float(prev["x"]) + float(current["x"])) / 2
        cy = (float(prev["y"]) + float(current["y"])) / 2
        wave = 12 if index % 2 else -10
        commands.append(f"Q {cx:.1f} {cy + wave:.1f} {float(current['x']):.1f} {float(current['y']):.1f}")
    return " ".join(commands)


def _turnaround_index(points: list[dict[str, Any]]) -> int:
    if len(points) < 2:
        return 0
    start = points[0]
    distances = [
        (float(point["x"]) - float(start["x"])) ** 2 + (float(point["y"]) - float(start["y"])) ** 2
        for point in points
    ]
    return max(range(len(points)), key=lambda index: distances[index])


def compute_route_layout(stops: list[dict[str, Any]], width: int = VIEWBOX_WIDTH, height: int = VIEWBOX_HEIGHT, options: dict[str, Any] | None = None) -> dict[str, Any]:
    options = options or {}
    warnings: list[str] = []
    ordered = sorted(stops, key=lambda item: int(item.get("order") or 9999))
    map_area = _map_area(width, height, options.get("mapPadding"))
    if len(ordered) < 2:
        warnings.append("not_enough_stops")

    resolved = []
    for index, stop in enumerate(ordered):
        lat, lng, source = resolve_stop_coordinate(stop)
        resolved.append((index, stop, lat, lng, source))

    points, bbox, mode = _project_coordinate_points(ordered, resolved, width, height, map_area, warnings)
    _disperse_close_points(points, map_area)
    _place_labels(points, map_area, warnings)

    source_counts = {
        "exact": sum(1 for point in points if point["confidence"] == "exact"),
        "cached": sum(1 for point in points if point["confidence"] == "cached"),
        "estimated": sum(1 for point in points if point["confidence"] == "estimated"),
        "fallback": sum(1 for point in points if point["confidence"] == "fallback"),
    }
    label_count = sum(1 for point in points if point["show_label"])
    inspection = "coordinate-based" if source_counts["exact"] else ("cached-based" if source_counts["cached"] else "fallback")
    route_path = _route_path(points)
    return {
        "mode": mode,
        "inspection": inspection,
        "viewBox": {"width": width, "height": height},
        "mapArea": map_area,
        "points": points,
        "routePath": route_path,
        "bbox": bbox,
        "warnings": warnings,
        "source_counts": source_counts,
        "labelCount": label_count,
        "label_count": label_count,
        "hidden_label_count": max(0, len(points) - label_count),
        "turnaround_index": _turnaround_index(points),
        "options": {"labelLimit": options.get("labelLimit", LABEL_LIMIT), "timelineLimit": options.get("timelineLimit", 8)},
    }


def render_album_route_svg(layout: dict[str, Any], options: dict[str, Any] | None = None) -> str:
    width = int(layout.get("viewBox", {}).get("width") or VIEWBOX_WIDTH)
    height = int(layout.get("viewBox", {}).get("height") or VIEWBOX_HEIGHT)
    points = layout.get("points") or []
    mode_label = "relative-position based" if layout.get("inspection") == "coordinate-based" else "estimated layout"
    route_path = layout.get("routePath") or _route_path(points)
    point_markup = []
    for index, point in enumerate(points):
        color = "#4CAF87" if index == 0 else "#F59E0B" if index == len(points) - 1 else "#2F80ED"
        fill = "#e9fff3" if index == 0 else "#fff3d9" if index == len(points) - 1 else "#eff7ff"
        point_markup.append(
            f"""
  <g class="route-marker" tabindex="0">
    <title>{escape(point['name'])}｜{escape(point.get('caption') or '')}</title>
    <circle cx="{point['x']}" cy="{point['y']}" r="14" fill="{fill}" stroke="{color}" stroke-width="4"/>
    <text x="{point['x']}" y="{float(point['y']) + 4:.1f}" text-anchor="middle" font-size="10" font-weight="900" fill="#173653">{int(point['order']):02d}</text>
  </g>"""
        )
        if point.get("show_label"):
            connector = point.get("labelConnector") or {}
            point_markup.append(
                f"""
  <path d="M {connector.get('x1', point['x'])} {connector.get('y1', point['y'])} L {connector.get('x2', point['x'])} {connector.get('y2', point['y'])}" stroke="#7eb7a0" stroke-width="1.2" opacity="0.58"/>
  <g class="route-label">
    <rect x="{point['labelX']}" y="{point['labelY']}" width="{point['labelWidth']}" height="{point['labelHeight']}" rx="13" fill="#fffaf0" stroke="#b8d8cc" filter="url(#softShadow)"/>
    <text x="{float(point['labelX']) + 10:.1f}" y="{float(point['labelY']) + 17:.1f}" font-size="12" font-weight="900" fill="#264653">{escape(point.get('labelLine1') or point['name'][:10])}</text>
    <text x="{float(point['labelX']) + 10:.1f}" y="{float(point['labelY']) + 32:.1f}" font-size="10" font-weight="700" fill="#6b7280">{escape(point.get('labelLine2') or '')}</text>
  </g>"""
            )
    warnings = "；".join(layout.get("warnings") or []) or "ok"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">Album Style Route</title>
  <desc id="desc">路线示意 / 非导航路线，不是精确导航路线。基于真实点位相对位置生成，风格化地图用于旅行相册展示，保留点位相对方位与顺序。</desc>
  <defs>
    <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="4" stdDeviation="5" flood-color="#236f58" flood-opacity="0.14"/>
    </filter>
  </defs>
  <rect width="{width}" height="{height}" rx="28" fill="#f7f1df"/>
  <path d="M0 110 C160 64 290 126 420 82 C590 26 738 62 1000 18 L1000 0 L0 0 Z" fill="#ecf6df" opacity="0.8"/>
  <path d="M20 470 C170 430 260 480 388 448 C520 418 642 456 770 424 C870 400 928 422 1000 386 L1000 680 L0 680 Z" fill="#e0f2da" opacity="0.95"/>
  <path d="M688 116 C760 76 892 92 930 164 C978 254 884 316 774 292 C692 274 610 180 688 116 Z" fill="#a9d8f5" opacity="0.64"/>
  <path d="M132 342 C220 270 308 298 382 236 C438 190 500 194 562 154" fill="none" stroke="#a9d8f5" stroke-width="10" opacity="0.32" stroke-linecap="round"/>
  <text x="36" y="44" font-size="24" font-weight="900" fill="#264653">Album Style Route</text>
  <text x="36" y="68" font-size="12" font-weight="800" fill="#6b7280">基于真实点位相对位置 · 路线示意 / 非导航路线</text>
  <g transform="translate(780 28)">
    <rect width="178" height="28" rx="14" fill="#fffaf0" stroke="#c8e2d6"/>
    <text x="16" y="18" font-size="12" font-weight="900" fill="#4CAF87">{mode_label}</text>
  </g>
  <path d="{route_path}" fill="none" stroke="#236f58" stroke-width="11" stroke-linecap="round" stroke-linejoin="round" opacity="0.12"/>
  <path d="{route_path}" fill="none" stroke="#4CAF87" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
  {''.join(point_markup)}
  <g transform="translate(36 {height - 72})">
    <rect width="{width - 72}" height="44" rx="16" fill="#fffaf0" stroke="#eadfbd"/>
    <text x="16" y="20" font-size="12" font-weight="900" fill="#264653">风格化地图用于旅行相册展示，保留点位相对方位与顺序，不是精确导航路线。</text>
    <text x="16" y="36" font-size="10" fill="#6b7280">debug: {escape(warnings[:120])}</text>
  </g>
</svg>
"""


def project_route_stops(stops: list[dict[str, Any]], width: int = VIEWBOX_WIDTH, height: int = VIEWBOX_HEIGHT) -> dict[str, Any]:
    layout = compute_route_layout(stops, width, height)
    bbox = layout["bbox"]
    return {
        "mode": layout["mode"],
        "inspection": layout["inspection"],
        "turnaround_index": layout["turnaround_index"],
        "view_box": {"width": width, "height": height},
        "mapArea": layout["mapArea"],
        "bbox": {
            "min_lng": bbox.get("minLng"),
            "max_lng": bbox.get("maxLng"),
            "min_lat": None,
            "max_lat": None,
            **bbox,
        },
        "aspect_ratio": None,
        "source_counts": layout["source_counts"],
        "label_count": layout["label_count"],
        "hidden_label_count": layout["hidden_label_count"],
        "points": [
            {
                **point,
                "normalized_x": None,
                "normalized_y": None,
                "label_position": point.get("labelAnchor"),
            }
            for point in layout["points"]
        ],
        "warnings": layout["warnings"],
        "routePath": layout["routePath"],
    }


computeRouteLayout = compute_route_layout
renderAlbumRouteSvg = render_album_route_svg
