# StoryAlbum Geo MVP

StoryAlbum Geo 是一个基于照片地址的旅行回忆与地图路线相册生成器。MVP 链路是：读取照片 EXIF GPS，使用 Python 调用高德逆地理编码补全地址和附近 POI，缓存静态地图图片，再生成可直接打开的网页成果展示。

## 范围

- P0：无 API 时生成本地可爱风路线图。
- MVP：EXIF GPS + 高德逆地理编码 + 高德静态地图 + 静态网页相册。
- P1：WGS84 到 GCJ-02 坐标转换、步行路线规划、视频模板渲染。

## 产物

- 照片清单：`assets/geo_album/meta/photo_manifest.csv`
- Stop 数据：`assets/geo_album/meta/geo_stops_enriched.json`
- 地图：`E:/W-项目学习/AI视频剪辑/assets/geo_album/maps/amap/geo_route_amap.png`
- 页面：`demo-site/index.html`


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
