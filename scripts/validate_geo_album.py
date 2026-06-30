from __future__ import annotations

from pathlib import Path

from geo_album_utils import (
    CACHE_DIR,
    DEMO_DATA_DIR,
    DOC_PRODUCT_DIR,
    DOC_SHOWCASE_DIR,
    MAP_AMAP_DIR,
    MAP_STYLED_DIR,
    META_DIR,
    PROJECT_ROOT,
    SOURCE_DIR,
    count_api_calls,
    ensure_geo_dirs,
    read_json,
)


REQUIRED_FILES = [
    META_DIR / "photo_manifest.csv",
    META_DIR / "photo_manifest.json",
    META_DIR / "geo_stops_raw.json",
    META_DIR / "geo_stops_enriched.json",
    DEMO_DATA_DIR / "geo_album.json",
]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _stop_lines(stops: list[dict]) -> str:
    if not stops:
        return "- 暂无 stop：需要带 GPS 的照片或手动地点。"
    lines = []
    for stop in stops:
        amap = stop.get("amap") or {}
        pois = amap.get("pois") or stop.get("pois") or []
        poi_text = "、".join(poi.get("name", "") for poi in pois if poi.get("name")) or "暂无 POI"
        lines.append(
            f"- {int(stop.get('order', 0)):02d}. {stop.get('name', '')}：{amap.get('formatted_address', stop.get('formattedAddress', '')) or '暂无地址'}；POI：{poi_text}；照片数：{stop.get('photo_count') or len(stop.get('photos', []))}"
        )
    return "\n".join(lines)


def _commands_doc() -> str:
    return """
## 运行流程

1. 在项目根目录创建 `.env.local`：
   `AMAP_WEB_SERVICE_KEY=your_key_here`
2. 扫描照片：`python scripts/scan_geo_photos.py`
3. 提取 EXIF：`python scripts/extract_geo_exif.py`
4. 生成 stop：`python scripts/build_geo_stops.py`
5. 逆地理编码 dry-run：`python scripts/amap_reverse_geocode.py --dry-run --max-calls 50`
6. 执行逆地理编码：`python scripts/amap_reverse_geocode.py --max-calls 50`
7. 生成高德静态地图 dry-run：`python scripts/amap_static_map.py --dry-run`
8. 执行静态地图生成：`python scripts/amap_static_map.py`
9. 如果 API 不可用，生成本地可爱路线：`python scripts/stylize_geo_route.py`
10. 生成网页配置：`python scripts/build_geo_album_config.py`
11. 打开网页：直接打开 `demo-site/index.html`
"""


def write_docs() -> None:
    manifest = read_json(META_DIR / "photo_manifest.json", default=[])
    raw = read_json(META_DIR / "geo_stops_raw.json", default={"stops": []})
    enriched = read_json(META_DIR / "geo_stops_enriched.json", default={"stops": []})
    album = read_json(DEMO_DATA_DIR / "geo_album.json", default={"stats": {}})
    log = read_json(CACHE_DIR / "amap_call_log.json", default=[])
    stats = album.get("stats", {})
    reverse_calls = sum(1 for item in log if item.get("type") == "reverse_geocode" and item.get("called_api"))
    static_calls = sum(1 for item in log if item.get("type") == "static_map" and item.get("called_api"))
    used_cache = (CACHE_DIR / "regeocode_cache.json").exists()
    map_path = MAP_AMAP_DIR / "geo_route_amap.png" if (MAP_AMAP_DIR / "geo_route_amap.png").exists() else MAP_STYLED_DIR / "cute_geo_route.svg"

    _write(
        DOC_PRODUCT_DIR / "storyalbum-geo-mvp.md",
        f"""
# StoryAlbum Geo MVP

StoryAlbum Geo 是一个基于照片地址的旅行回忆与地图路线相册生成器。MVP 链路是：读取照片 EXIF GPS，使用 Python 调用高德逆地理编码补全地址和附近 POI，缓存静态地图图片，再生成可直接打开的网页成果展示。

## 范围

- P0：无 API 时生成本地可爱风路线图。
- MVP：EXIF GPS + 高德逆地理编码 + 高德静态地图 + 静态网页相册。
- P1：WGS84 到 GCJ-02 坐标转换、步行路线规划、视频模板渲染。

## 产物

- 照片清单：`assets/geo_album/meta/photo_manifest.csv`
- Stop 数据：`assets/geo_album/meta/geo_stops_enriched.json`
- 地图：`{map_path.as_posix()}`
- 页面：`demo-site/index.html`

{_commands_doc()}
""",
    )

    _write(
        DOC_SHOWCASE_DIR / "geo-processing-report.md",
        f"""
# Geo Processing Report

- 源图片文件夹：`{SOURCE_DIR}`
- 总图片数：{len(manifest)}
- 有 GPS 数：{sum(1 for row in manifest if row.get('has_gps'))}
- 无 GPS 数：{sum(1 for row in manifest if not row.get('has_gps'))}
- 生成 stop 数：{len(enriched.get('stops', []))}
- 高德逆地理编码调用次数：{reverse_calls}
- 高德静态地图调用次数：{static_calls}
- 是否使用缓存：{'是' if used_cache else '否'}
- 是否存在坐标偏移风险：是。照片 EXIF GPS 通常为 WGS84，高德使用 GCJ-02，当前 MVP 未做坐标转换。
- 输出地图路径：`{map_path}`
- demo 页面路径：`{PROJECT_ROOT / 'demo-site' / 'index.html'}`

## Stop 明细

{_stop_lines(enriched.get('stops', []))}

## 调用失败记录

{chr(10).join(f"- {item.get('type')}: {item.get('error')}" for item in log if item.get('error')) or "- 暂无失败记录。"}
""",
    )

    _write(
        DOC_SHOWCASE_DIR / "amap-api-notes.md",
        """
# AMap API Notes

- 使用了高德逆地理编码 API：由 `scripts/amap_reverse_geocode.py` 在 Python 中调用。
- 使用了高德静态地图 API：由 `scripts/amap_static_map.py` 在 Python 中调用。
- Key 不在前端暴露：`demo-site` 只读取本地 JSON 和缓存图片，不请求高德 API。
- API 结果本地缓存：逆地理编码写入 `assets/geo_album/cache/regeocode_cache.json`，调用日志写入 `assets/geo_album/cache/amap_call_log.json`。
- 保存的 URL 会将 `key` 脱敏为 `key=***`。
- 照片 GPS 与高德坐标系可能存在偏移：EXIF 多为 WGS84，高德地图使用 GCJ-02。
- 下一步可接高德坐标转换 API，或增加本地 WGS84 到 GCJ-02 转换模块。
""",
    )

    _write(
        DOC_SHOWCASE_DIR / "cache-and-quota-notes.md",
        """
# Cache And Quota Notes

- 当前默认 `--max-calls=50`，逆地理编码和静态地图脚本都支持该参数。
- dry-run：`python scripts/amap_reverse_geocode.py --dry-run --max-calls 50` 和 `python scripts/amap_static_map.py --dry-run`。
- force-refresh：`python scripts/amap_reverse_geocode.py --force-refresh --max-calls 50` 或 `python scripts/amap_static_map.py --force-refresh`。
- 缓存文件位置：`assets/geo_album/cache/regeocode_cache.json`。
- 调用日志位置：`assets/geo_album/cache/amap_call_log.json`。
- 避免重复调用：脚本会优先读取缓存；只有坐标缓存缺失或显式 `--force-refresh` 时才请求 API。
""",
    )

    _write(
        DOC_SHOWCASE_DIR / "manual-route-adjustment.md",
        """
# Manual Route Adjustment

- 改 stop 顺序：编辑 `assets/geo_album/meta/geo_stops_enriched.json` 中每个 stop 的 `order`，再运行 `python scripts/build_geo_album_config.py`。
- 改地点名称：编辑 stop 的 `name` 字段，再重新生成网页配置。
- 改 caption：编辑 stop 的 `caption` 字段，再重新生成网页配置。
- 替换 cover：编辑 `demo-site/data/geo_album.json` 的 `cover` 字段，或调整 `photo_manifest.json` 中第一张 GPS 照片顺序后重新生成配置。
- 无 API 情况下使用 cute route：运行 `python scripts/stylize_geo_route.py`，再运行 `python scripts/build_geo_album_config.py`，页面会使用 `assets/geo_album/maps/styled/cute_geo_route.svg`。
""",
    )

    _write(
        DOC_SHOWCASE_DIR / "result-showcase-copy.md",
        """
# Result Showcase Copy

StoryAlbum Geo｜基于照片地址的旅行回忆相册

从一组带 GPS 的旅行照片出发，自动读取拍摄时间和坐标，补全地址与附近 POI，生成路线地图、点位卡片和照片墙。前端页面只展示已缓存成果，不暴露任何地图 API Key。

三步表达：

照片输入 → 地理信息结构化 → 地图相册输出
""",
    )


def validate() -> int:
    ensure_geo_dirs()
    missing = [str(path) for path in REQUIRED_FILES if not path.exists()]
    map_exists = (MAP_AMAP_DIR / "geo_route_amap.png").exists() or (MAP_STYLED_DIR / "cute_geo_route.svg").exists() or (MAP_STYLED_DIR / "cute_geo_route.png").exists()
    album = read_json(DEMO_DATA_DIR / "geo_album.json", default={})
    problems = []
    if missing:
        problems.append("missing_required_files=" + ", ".join(missing))
    if not map_exists:
        problems.append("missing_route_map")
    if "AMAP_WEB_SERVICE_KEY" in (PROJECT_ROOT / "demo-site" / "app.js").read_text(encoding="utf-8", errors="ignore"):
        problems.append("front_end_contains_env_var_name")
    write_docs()
    print(f"required_files_missing={len(missing)}")
    print(f"map_exists={map_exists}")
    print(f"api_call_count={count_api_calls(CACHE_DIR / 'amap_call_log.json')}")
    print(f"demo={PROJECT_ROOT / 'demo-site' / 'index.html'}")
    if problems:
        for problem in problems:
            print(problem)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(validate())

