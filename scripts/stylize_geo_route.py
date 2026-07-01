from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from geo_album_utils import MAP_STYLED_DIR, META_DIR, ensure_geo_dirs, read_json
from route_projection import VIEWBOX_HEIGHT, VIEWBOX_WIDTH, computeRouteLayout, renderAlbumRouteSvg


SVG_PATH = MAP_STYLED_DIR / "cute_geo_route.svg"
PNG_PATH = MAP_STYLED_DIR / "cute_geo_route.png"
METADATA_PATH = MAP_STYLED_DIR / "cute_geo_route_projection.json"


def _load_stops() -> list[dict]:
    enriched = read_json(META_DIR / "geo_stops_enriched.json", default=None)
    if enriched:
        return enriched.get("stops", [])
    raw = read_json(META_DIR / "geo_stops_raw.json", default={"stops": []})
    return raw.get("stops", [])


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"]:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def _sample_quadratic_route(points: list[dict]) -> list[tuple[float, float]]:
    if len(points) <= 1:
        return [(float(point["x"]), float(point["y"])) for point in points]
    if len(points) == 2:
        return [(float(points[0]["x"]), float(points[0]["y"])), (float(points[1]["x"]), float(points[1]["y"]))]
    sampled: list[tuple[float, float]] = []
    ordered = sorted(points, key=lambda point: int(point["order"]))
    for index in range(1, len(ordered)):
        prev = ordered[index - 1]
        current = ordered[index]
        cx = (float(prev["x"]) + float(current["x"])) / 2
        cy = (float(prev["y"]) + float(current["y"])) / 2 + (12 if index % 2 else -10)
        for step in range(18):
            t = step / 18
            x = (1 - t) ** 2 * float(prev["x"]) + 2 * (1 - t) * t * cx + t**2 * float(current["x"])
            y = (1 - t) ** 2 * float(prev["y"]) + 2 * (1 - t) * t * cy + t**2 * float(current["y"])
            sampled.append((x, y))
    sampled.append((float(ordered[-1]["x"]), float(ordered[-1]["y"])))
    return sampled


def _write_png(layout: dict) -> None:
    image = Image.new("RGB", (VIEWBOX_WIDTH, VIEWBOX_HEIGHT), "#f7f1df")
    draw = ImageDraw.Draw(image)
    draw.polygon([(0, 0), (0, 110), (160, 64), (290, 126), (420, 82), (590, 26), (738, 62), (1000, 18), (1000, 0)], fill="#ecf6df")
    draw.polygon([(0, 680), (0, 470), (170, 430), (260, 480), (388, 448), (520, 418), (642, 456), (770, 424), (1000, 386), (1000, 680)], fill="#e0f2da")
    draw.ellipse((666, 84, 948, 318), fill="#a9d8f5")
    draw.arc((120, 300, 580, 432), 188, 340, fill="#a9d8f5", width=10)

    title_font = _font(24)
    small_font = _font(12)
    label_font = _font(12)
    marker_font = _font(10)
    draw.text((36, 20), "Album Style Route", fill="#264653", font=title_font)
    draw.text((36, 54), "路线示意 / 非导航路线", fill="#6b7280", font=small_font)
    draw.rounded_rectangle((780, 28, 958, 56), radius=14, fill="#fffaf0", outline="#c8e2d6")
    draw.text((796, 36), "relative-position based", fill="#4CAF87", font=small_font)

    route = _sample_quadratic_route(layout.get("points") or [])
    if len(route) > 1:
        draw.line(route, fill="#d5e4d9", width=11, joint="curve")
        draw.line(route, fill="#4CAF87", width=4, joint="curve")

    points = layout.get("points") or []
    for index, point in enumerate(points):
        color = "#4CAF87" if index == 0 else "#F59E0B" if index == len(points) - 1 else "#2F80ED"
        fill = "#e9fff3" if index == 0 else "#fff3d9" if index == len(points) - 1 else "#eff7ff"
        x = float(point["x"])
        y = float(point["y"])
        draw.ellipse((x - 14, y - 14, x + 14, y + 14), fill=fill, outline=color, width=4)
        draw.text((x - 9, y - 7), f"{int(point['order']):02d}", fill="#173653", font=marker_font)
        if point.get("show_label"):
            lx = float(point["labelX"])
            ly = float(point["labelY"])
            lw = float(point["labelWidth"])
            lh = float(point["labelHeight"])
            connector = point.get("labelConnector") or {}
            draw.line(
                [
                    (float(connector.get("x1", x)), float(connector.get("y1", y))),
                    (float(connector.get("x2", lx + lw / 2)), float(connector.get("y2", ly + lh / 2))),
                ],
                fill="#9bcab7",
                width=1,
            )
            draw.rounded_rectangle((lx, ly, lx + lw, ly + lh), radius=13, fill="#fffaf0", outline="#b8d8cc")
            draw.text((lx + 10, ly + 5), str(point.get("labelLine1") or point["name"][:10]), fill="#264653", font=label_font)
            if point.get("labelLine2"):
                draw.text((lx + 10, ly + 21), str(point["labelLine2"]), fill="#6b7280", font=marker_font)

    draw.rounded_rectangle((36, VIEWBOX_HEIGHT - 72, VIEWBOX_WIDTH - 36, VIEWBOX_HEIGHT - 28), radius=16, fill="#fffaf0", outline="#eadfbd")
    draw.text((52, VIEWBOX_HEIGHT - 60), "风格化地图用于旅行相册展示，保留点位相对方位与顺序，不代表导航路径。", fill="#264653", font=small_font)
    image.save(PNG_PATH)


def main() -> None:
    ensure_geo_dirs()
    stops = _load_stops()
    layout = computeRouteLayout(stops, VIEWBOX_WIDTH, VIEWBOX_HEIGHT)
    SVG_PATH.write_text(renderAlbumRouteSvg(layout), encoding="utf-8")
    _write_png(layout)
    METADATA_PATH.write_text(json.dumps(layout, ensure_ascii=False, indent=2), encoding="utf-8")
    for warning in layout.get("warnings") or []:
        print(f"layout_warning={warning}")
    print(f"mode={layout['mode']}")
    print(f"inspection={layout['inspection']}")
    print(f"label_count={layout['label_count']}")
    print(f"hidden_label_count={layout['hidden_label_count']}")
    print(f"bbox={layout['bbox']}")
    print(f"svg={SVG_PATH}")
    print(f"png={PNG_PATH}")
    print(f"metadata={METADATA_PATH}")


if __name__ == "__main__":
    main()
