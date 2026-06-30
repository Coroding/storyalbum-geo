# Cache And Quota Notes

- 当前默认 `--max-calls=50`，逆地理编码和静态地图脚本都支持该参数。
- dry-run：`python scripts/amap_reverse_geocode.py --dry-run --max-calls 50` 和 `python scripts/amap_static_map.py --dry-run`。
- force-refresh：`python scripts/amap_reverse_geocode.py --force-refresh --max-calls 50` 或 `python scripts/amap_static_map.py --force-refresh`。
- 缓存文件位置：`assets/geo_album/cache/regeocode_cache.json`。
- 调用日志位置：`assets/geo_album/cache/amap_call_log.json`。
- 避免重复调用：脚本会优先读取缓存；只有坐标缓存缺失或显式 `--force-refresh` 时才请求 API。
