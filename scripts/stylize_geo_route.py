from __future__ import annotations

import json
from html import escape
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from geo_album_utils import MAP_STYLED_DIR, META_DIR, ensure_geo_dirs, read_json
from route_projection import VIEWBOX_HEIGHT, VIEWBOX_WIDTH, project_route_stops


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


def _label_xy(point: dict, width: int = 158, height: int = 36) -> tuple[float, float]:
    position = point.get("label_position")
    x = float(point["x"])
    y = float(point["y"])
    if position == "left":
        lx, ly = x - width - 18, y - height / 2
    if position == "top":
        lx, ly = x - width / 2, y - height - 20
    elif position == "bottom":
        lx, ly = x - width / 2, y + 20
    elif position == "left-top":
        lx, ly = x - width - 14, y - height - 14
    elif position == "right-top":
        lx, ly = x + 14, y - height - 14
    elif position != "left":
        lx, ly = x + 18, y - height / 2
    lx = max(16, min(VIEWBOX_WIDTH - width - 16, lx))
    ly = max(106, min(VIEWBOX_HEIGHT - height - 46, ly))
    return lx, ly


def _route_path(points: list[dict]) -> str:
    if not points:
        return ""
    if len(points) == 1:
        return f"M {points[0]['x']} {points[0]['y']}"
    commands = [f"M {points[0]['x']:.1f} {points[0]['y']:.1f}"]
    for index in range(1, len(points)):
        prev = points[index - 1]
        current = points[index]
        cx = (float(prev["x"]) + float(current["x"])) / 2
        cy = (float(prev["y"]) + float(current["y"])) / 2
        wave = 28 if index % 2 else -24
        commands.append(f"Q {cx:.1f} {cy + wave:.1f} {float(current['x']):.1f} {float(current['y']):.1f}")
    return " ".join(commands)


def _route_segments(points: list[dict], projection: dict) -> tuple[list[dict], list[dict]]:
    if len(points) <= 2:
        return points, []
    split = int(projection.get("turnaround_index") or len(points) - 1)
    split = max(1, min(split, len(points) - 1))
    primary = points[: split + 1]
    secondary = points[split:] if split < len(points) - 1 else []
    return primary, secondary


def _point_markup(points: list[dict]) -> str:
    chunks = []
    total = len(points)
    for index, point in enumerate(points):
        x = float(point["x"])
        y = float(point["y"])
        order = int(point["order"])
        name = escape(str(point["name"]))
        confidence = escape(str(point["confidence"]))
        is_start = index == 0
        is_end = index == total - 1
        outer = "#f59e0b" if is_start else "#38bdf8" if is_end else "#4fa787"
        fill = "#fff7df" if is_start else "#e8f7ff" if is_end else "#ffffff"
        title = f"{name}｜照片 {point.get('photo_count', 0)}｜{confidence}"
        chunks.append(
            f"""
  <g class="route-point" tabindex="0" aria-label="{title}">
    <title>{title}</title>
    <circle cx="{x:.1f}" cy="{y:.1f}" r="18" fill="{fill}" stroke="{outer}" stroke-width="5"/>
    <circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{outer}"/>
    <text x="{x:.1f}" y="{y + 6:.1f}" text-anchor="middle" font-size="13" font-weight="900" fill="#264653">{order:02d}</text>
  </g>"""
        )
        if point.get("show_label"):
            lx, ly = _label_xy(point)
            chunks.append(
                f"""
  <g class="route-label">
    <rect x="{lx:.1f}" y="{ly:.1f}" width="158" height="36" rx="15" fill="#fffaf0" stroke="#d7ead4"/>
    <text x="{lx + 14:.1f}" y="{ly + 23:.1f}" font-size="15" font-weight="800" fill="#264653">{name[:10]}</text>
  </g>"""
            )
    return "".join(chunks)


def _chips_markup(points: list[dict]) -> str:
    chunks = []
    for index, point in enumerate(points):
        x = 42 + (index % 6) * 152
        y = 574 + (index // 6) * 34
        name = escape(str(point["name"])[:8])
        chunks.append(
            f"""<g><rect x="{x}" y="{y}" width="136" height="24" rx="12" fill="#ffffff" opacity="0.82"/><text x="{x + 10}" y="{y + 16}" font-size="12" font-weight="700" fill="#56726b">{int(point['order']):02d} {name}</text></g>"""
        )
    return "".join(chunks)


def _write_svg(stops: list[dict], projection: dict) -> None:
    points = projection["points"]
    if not points:
        points = project_route_stops([{"order": 1, "name": "等待照片 GPS"}])["points"]
    primary_points, secondary_points = _route_segments(points, projection)
    path_d = _route_path(primary_points)
    secondary_d = _route_path(secondary_points)
    mode_label = {
        "coordinate-based": "coordinate-based",
        "order-based fallback": "estimated layout",
    }.get(projection["mode"], projection["mode"])
    hidden = projection.get("hidden_label_count", 0)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{VIEWBOX_WIDTH}" height="{VIEWBOX_HEIGHT}" viewBox="0 0 {VIEWBOX_WIDTH} {VIEWBOX_HEIGHT}" role="img" aria-labelledby="title desc">
  <title id="title">StoryAlbum Geo Album Style Route Map</title>
  <desc id="desc">基于真实点位相对位置的风格化路线示意图，不是精确导航路线。</desc>
  <style>
    :root {{
      --map-bg: #f7f1df;
      --map-paper: #fffaf0;
      --map-green: #b9d99a;
      --map-water: #a9d8f5;
      --route-main: #4fa787;
      --route-shadow: rgba(35, 111, 88, 0.18);
      --start: #f59e0b;
      --end: #38bdf8;
      --ink: #264653;
      --muted: #6b7280;
      --card: #ffffff;
    }}
    text {{ font-family: "Microsoft YaHei", "PingFang SC", system-ui, sans-serif; }}
    .route-point:hover + .route-label rect,
    .route-point:focus + .route-label rect {{ stroke: #4fa787; stroke-width: 2; }}
  </style>
  <rect width="1000" height="680" rx="34" fill="var(--map-bg)"/>
  <path d="M0 108 C180 74 290 126 416 80 C578 20 722 62 1000 18 L1000 0 L0 0 Z" fill="#eff8df" opacity="0.85"/>
  <path d="M42 488 C174 444 248 496 376 462 C518 424 626 472 770 438 C864 416 928 438 1000 402 L1000 680 L0 680 Z" fill="#e4f4dc" opacity="0.95"/>
  <path d="M678 126 C758 70 904 80 940 160 C978 244 880 308 780 288 C692 270 606 188 678 126 Z" fill="var(--map-water)" opacity="0.68"/>
  <path d="M700 164 C760 126 872 128 908 182" fill="none" stroke="#ffffff" stroke-width="8" opacity="0.48" stroke-linecap="round"/>
  <path d="M108 340 C196 268 290 304 358 242 C420 186 478 202 548 160" fill="none" stroke="#a9d8f5" stroke-width="13" opacity="0.38" stroke-linecap="round"/>
  <circle cx="138" cy="128" r="58" fill="#fff5cb" opacity="0.72"/>
  <circle cx="186" cy="86" r="7" fill="#f6c76f"/>
  <circle cx="834" cy="92" r="6" fill="#f6c76f"/>
  <path d="M86 210 l18 -10 l18 10 l-18 10 Z" fill="#f59e0b" opacity="0.7"/>
  <path d="M904 352 l15 -9 l15 9 l-15 9 Z" fill="#38bdf8" opacity="0.72"/>
  <g opacity="0.28">
    <path d="M46 72 h100 M72 108 h82 M810 532 h120 M768 568 h156" stroke="#d6cba7" stroke-width="3" stroke-linecap="round"/>
  </g>
  <text x="42" y="58" font-size="30" font-weight="900" fill="var(--ink)">Album Style Route</text>
  <text x="42" y="88" font-size="15" font-weight="700" fill="var(--muted)">基于真实点位相对位置 · 不含前端高德 API 请求</text>
  <g transform="translate(760 34)">
    <rect width="196" height="32" rx="16" fill="#ffffff" opacity="0.84"/>
    <text x="18" y="21" font-size="13" font-weight="900" fill="#4fa787">{mode_label}</text>
  </g>
  <path d="{path_d}" fill="none" stroke="#236f58" stroke-width="22" stroke-linecap="round" stroke-linejoin="round" opacity="0.16"/>
  <path d="{path_d}" fill="none" stroke="var(--route-main)" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="{path_d}" fill="none" stroke="#fffaf0" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" opacity="0.72"/>
  <path d="{secondary_d}" fill="none" stroke="#236f58" stroke-width="12" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="12 14" opacity="0.12"/>
  <path d="{secondary_d}" fill="none" stroke="#4fa787" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="10 13" opacity="0.58"/>
  {_point_markup(points)}
  <g>
    <rect x="36" y="520" width="928" height="122" rx="24" fill="#fffaf0" opacity="0.78" stroke="#efe2bd"/>
    <text x="58" y="552" font-size="15" font-weight="900" fill="#264653">完整停靠点 timeline · 主图隐藏 {hidden} 个拥挤标签，可 hover/tap 点位查看</text>
    {_chips_markup(points)}
  </g>
  <text x="42" y="662" font-size="13" fill="#6b7280">风格化地图保留点位相对方位与顺序，用于旅行相册展示；不是精确导航路线。</text>
</svg>
"""
    SVG_PATH.write_text(svg, encoding="utf-8")


def _sampled_route(points: list[dict]) -> list[tuple[float, float]]:
    if len(points) <= 1:
        return [(float(point["x"]), float(point["y"])) for point in points]
    sampled = []
    for index in range(1, len(points)):
        prev = points[index - 1]
        current = points[index]
        cx = (float(prev["x"]) + float(current["x"])) / 2
        cy = (float(prev["y"]) + float(current["y"])) / 2 + (28 if index % 2 else -24)
        for step in range(18):
            t = step / 18
            x = (1 - t) ** 2 * float(prev["x"]) + 2 * (1 - t) * t * cx + t**2 * float(current["x"])
            y = (1 - t) ** 2 * float(prev["y"]) + 2 * (1 - t) * t * cy + t**2 * float(current["y"])
            sampled.append((x, y))
    sampled.append((float(points[-1]["x"]), float(points[-1]["y"])))
    return sampled


def _write_png(projection: dict) -> None:
    scale = 1
    image = Image.new("RGB", (VIEWBOX_WIDTH * scale, VIEWBOX_HEIGHT * scale), "#f7f1df")
    draw = ImageDraw.Draw(image)
    draw.ellipse((620, 82, 948, 310), fill="#a9d8f5")
    draw.polygon([(0, 680), (0, 525), (180, 472), (330, 500), (520, 448), (710, 472), (1000, 410), (1000, 680)], fill="#e4f4dc")
    draw.ellipse((80, 72, 196, 188), fill="#fff5cb")

    points = projection["points"]
    primary_points, secondary_points = _route_segments(points, projection)
    route = _sampled_route(primary_points)
    if len(route) > 1:
        draw.line(route, fill="#c7ded2", width=22, joint="curve")
        draw.line(route, fill="#4fa787", width=8, joint="curve")
        draw.line(route, fill="#fffaf0", width=3, joint="curve")
    secondary = _sampled_route(secondary_points)
    if len(secondary) > 1:
        for idx in range(0, len(secondary) - 1, 4):
            segment = secondary[idx : idx + 3]
            if len(segment) > 1:
                draw.line(segment, fill="#8ec6aa", width=4, joint="curve")

    title_font = _font(30)
    small_font = _font(15)
    label_font = _font(15)
    number_font = _font(13)
    draw.text((42, 28), "Album Style Route", fill="#264653", font=title_font)
    draw.text((42, 70), "基于真实点位相对位置 · 不是精确导航路线", fill="#6b7280", font=small_font)
    draw.rounded_rectangle((760, 34, 956, 66), radius=16, fill="#fffaf0", outline="#d7ead4")
    draw.text((778, 42), projection["mode"], fill="#4fa787", font=number_font)

    for index, point in enumerate(points):
        x = float(point["x"])
        y = float(point["y"])
        outline = "#f59e0b" if index == 0 else "#38bdf8" if index == len(points) - 1 else "#4fa787"
        fill = "#fff7df" if index == 0 else "#e8f7ff" if index == len(points) - 1 else "#ffffff"
        draw.ellipse((x - 18, y - 18, x + 18, y + 18), fill=fill, outline=outline, width=5)
        draw.text((x - 10, y - 8), f"{int(point['order']):02d}", fill="#264653", font=number_font)
        if point.get("show_label"):
            lx, ly = _label_xy(point)
            draw.rounded_rectangle((lx, ly, lx + 158, ly + 36), radius=15, fill="#fffaf0", outline="#d7ead4")
            draw.text((lx + 14, ly + 8), str(point["name"])[:10], fill="#264653", font=label_font)

    image.save(PNG_PATH)


def main() -> None:
    ensure_geo_dirs()
    stops = _load_stops()
    projection = project_route_stops(stops)
    _write_svg(stops, projection)
    _write_png(projection)
    METADATA_PATH.write_text(json.dumps(projection, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"mode={projection['mode']}")
    print(f"inspection={projection['inspection']}")
    print(f"label_count={projection['label_count']}")
    print(f"hidden_label_count={projection['hidden_label_count']}")
    print(f"bbox={projection['bbox']}")
    print(f"svg={SVG_PATH}")
    print(f"png={PNG_PATH}")
    print(f"metadata={METADATA_PATH}")


if __name__ == "__main__":
    main()
