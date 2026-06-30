# Manual Route Adjustment

- 改 stop 顺序：编辑 `assets/geo_album/meta/geo_stops_enriched.json` 中每个 stop 的 `order`，再运行 `python scripts/build_geo_album_config.py`。
- 改地点名称：编辑 stop 的 `name` 字段，再重新生成网页配置。
- 改 caption：编辑 stop 的 `caption` 字段，再重新生成网页配置。
- 替换 cover：编辑 `demo-site/data/geo_album.json` 的 `cover` 字段，或调整 `photo_manifest.json` 中第一张 GPS 照片顺序后重新生成配置。
- 无 API 情况下使用 cute route：运行 `python scripts/stylize_geo_route.py`，再运行 `python scripts/build_geo_album_config.py`，页面会使用 `assets/geo_album/maps/styled/cute_geo_route.svg`。
