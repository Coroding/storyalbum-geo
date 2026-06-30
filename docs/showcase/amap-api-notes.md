# AMap API Notes

- 使用了高德逆地理编码 API：由 `scripts/amap_reverse_geocode.py` 在 Python 中调用。
- 使用了高德静态地图 API：由 `scripts/amap_static_map.py` 在 Python 中调用。
- Key 不在前端暴露：`demo-site` 只读取本地 JSON 和缓存图片，不请求高德 API。
- API 结果本地缓存：逆地理编码写入 `assets/geo_album/cache/regeocode_cache.json`，调用日志写入 `assets/geo_album/cache/amap_call_log.json`。
- 保存的 URL 会将 `key` 脱敏为 `key=***`。
- 照片 GPS 与高德坐标系可能存在偏移：EXIF 多为 WGS84，高德地图使用 GCJ-02。
- 下一步可接高德坐标转换 API，或增加本地 WGS84 到 GCJ-02 转换模块。
