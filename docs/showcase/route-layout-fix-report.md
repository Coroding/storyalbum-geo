# StoryAlbum Geo 路线布局修复报告

## 问题诊断

- 旧版 Album Style 图使用经纬度近似映射后，没有独立的地图绘图区，底部 timeline 被画进 SVG，压到了地图主视觉。
- 旧版投影没有使用 Web Mercator，丽江到泸沽湖这种经纬跨度差异较大的路线容易被拉成不可信的视觉关系。
- 旧版没有严格的 `top/bottom/left/right` 绘图区边界，点位和标签容易贴边。
- 近距离点位只做轻微 jitter，没有按屏幕距离聚合分散，丽江和泸沽湖附近 marker 容易重叠。
- 标签避让只按象限放置，没有计算候选标签 bbox 与已放标签、marker、边界的冲突。
- SVG 内嵌完整 timeline，导致底部信息挤压地图，页面上方也显得主视觉不集中。

## 修复策略

- 新增 `computeRouteLayout(stops, width, height, options)`，将 route-data、layout 和 render 分层。
- 使用 Web Mercator 近似投影：`xMerc = lng*pi/180`，`yMerc = ln(tan(pi/4 + lat*pi/360))`，保证 x/y 使用一致量纲，避免路线被压成横线。
- 绘图区固定为 `left=72`、`right=width-72`、`top=80`、`bottom=height-160`，底部只保留一句 legend。
- bbox 使用最小跨度阈值 `0.001`，并按较小缩放因子居中适配绘图区，避免点位贴边或挤角。
- 屏幕距离小于 `28px` 的点位视为 close points，围绕中心做 18-28px 环形分散。
- 标签最多显示 6 个；每个标签从 8 个候选位置中选择冲突面积最小的位置，并绘制 connector。
- timeline 从 SVG 移到页面下方 chips，默认显示前 8 个，可展开全部。

## 当前结果

- 投影模式：`coordinate-based`
- 点位来源：`assets/geo_album/meta/geo_stops_enriched.json` 中的 `centroid_wgs84`
- 地图输出：`assets/geo_album/maps/styled/cute_geo_route.svg`
- metadata 输出：`assets/geo_album/maps/styled/cute_geo_route_projection.json`
- 页面说明：风格化地图用于旅行相册展示，保留点位相对方位与顺序，不代表导航路径。

## 风险

- 当前照片坐标是 WGS84，高德静态图使用 GCJ-02，仍存在坐标系偏移风险。
- 丽江和泸沽湖内部点位非常密集，自动避让会隐藏部分标签，完整点位放在页面 timeline。
