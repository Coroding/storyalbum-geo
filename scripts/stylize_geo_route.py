from __future__ import annotations

from math import sin
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from geo_album_utils import MAP_STYLED_DIR, META_DIR, ensure_geo_dirs, read_json


SVG_PATH = MAP_STYLED_DIR / "cute_geo_route.svg"
PNG_PATH = MAP_STYLED_DIR / "cute_geo_route.png"


def _load_stops() -> list[dict]:
    enriched = read_json(META_DIR / "geo_stops_enriched.json", default=None)
    if enriched:
        return enriched.get("stops", [])
    raw = read_json(META_DIR / "geo_stops_raw.json", default={"stops": []})
    return raw.get("stops", [])


def _layout_points(count: int) -> list[tuple[int, int]]:
    if count <= 0:
        return []
    points = []
    top = 160
    bottom = 920
    step = (bottom - top) / max(count - 1, 1)
    for index in range(count):
        y = int(top + step * index)
        x = 210 if index % 2 == 0 else 510
        points.append((x, y))
    return points


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"]:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def _write_svg(stops: list[dict], points: list[tuple[int, int]]) -> None:
    if not stops:
        stops = [{"order": 1, "name": "等待照片 GPS", "caption": "请补充带 GPS 的照片"}]
        points = [(375, 500)]
    path_d = ""
    if points:
        path_d = f"M {points[0][0]} {points[0][1]} "
        for index, point in enumerate(points[1:], start=1):
            prev = points[index - 1]
            cx = (prev[0] + point[0]) / 2
            cy = (prev[1] + point[1]) / 2 - 70
            path_d += f"Q {cx:.0f} {cy:.0f} {point[0]} {point[1]} "
    stop_markup = []
    for stop, (x, y) in zip(stops, points):
        label = str(stop.get("name") or f"地点 {stop.get('order', 1):02d}")
        number = f"{int(stop.get('order', 1)):02d}"
        label_x = x + 54 if x < 375 else x - 244
        stop_markup.append(
            f"""
  <g>
    <circle cx="{x}" cy="{y}" r="38" fill="#ffffff" stroke="#55a6d9" stroke-width="5"/>
    <circle cx="{x}" cy="{y}" r="26" fill="#9bd9c3"/>
    <text x="{x}" y="{y + 8}" text-anchor="middle" font-size="20" font-weight="800" fill="#174b6d">{number}</text>
    <rect x="{label_x}" y="{y - 19}" width="190" height="38" rx="14" fill="#ffffff" stroke="#d7ecf7"/>
    <text x="{label_x + 16}" y="{y + 7}" font-size="17" font-weight="700" fill="#174b6d">{label[:10]}</text>
  </g>"""
        )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="750" height="1000" viewBox="0 0 750 1000">
  <rect width="750" height="1000" fill="#f8fcf6"/>
  <circle cx="620" cy="120" r="110" fill="#dff3ff"/>
  <circle cx="100" cy="840" r="140" fill="#e1f7e8"/>
  <path d="{path_d}" fill="none" stroke="#55a6d9" stroke-width="16" stroke-linecap="round" stroke-linejoin="round" opacity="0.28"/>
  <path d="{path_d}" fill="none" stroke="#2f80a8" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
  <text x="54" y="76" font-size="32" font-weight="800" fill="#174b6d">StoryAlbum Geo</text>
  <text x="54" y="112" font-size="18" fill="#5a7d8f">路线示意 · 本地图形降级方案</text>
  {''.join(stop_markup)}
</svg>
"""
    SVG_PATH.write_text(svg, encoding="utf-8")


def _write_png(stops: list[dict], points: list[tuple[int, int]]) -> None:
    if not stops:
        stops = [{"order": 1, "name": "等待照片 GPS"}]
        points = [(375, 500)]
    image = Image.new("RGB", (750, 1000), "#f8fcf6")
    draw = ImageDraw.Draw(image)
    draw.ellipse((510, 10, 730, 230), fill="#dff3ff")
    draw.ellipse((-40, 700, 240, 980), fill="#e1f7e8")
    if len(points) > 1:
        draw.line(points, fill="#55a6d9", width=18, joint="curve")
        draw.line(points, fill="#2f80a8", width=6, joint="curve")
    title_font = _font(32)
    small_font = _font(18)
    label_font = _font(19)
    draw.text((54, 42), "StoryAlbum Geo", fill="#174b6d", font=title_font)
    draw.text((54, 90), "路线示意 · 本地图形降级方案", fill="#5a7d8f", font=small_font)
    for stop, (x, y) in zip(stops, points):
        draw.ellipse((x - 38, y - 38, x + 38, y + 38), fill="#ffffff", outline="#55a6d9", width=5)
        draw.ellipse((x - 26, y - 26, x + 26, y + 26), fill="#9bd9c3")
        number = f"{int(stop.get('order', 1)):02d}"
        draw.text((x - 15, y - 13), number, fill="#174b6d", font=label_font)
        label = str(stop.get("name") or number)[:10]
        lx = x + 54 if x < 375 else x - 244
        draw.rounded_rectangle((lx, y - 19, lx + 190, y + 19), radius=14, fill="#ffffff", outline="#d7ecf7")
        draw.text((lx + 16, y - 12), label, fill="#174b6d", font=label_font)
    image.save(PNG_PATH)


def main() -> None:
    ensure_geo_dirs()
    stops = _load_stops()
    points = _layout_points(len(stops))
    _write_svg(stops, points)
    _write_png(stops, points)
    print(f"svg={SVG_PATH}")
    print(f"png={PNG_PATH}")


if __name__ == "__main__":
    main()
