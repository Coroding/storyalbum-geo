# StoryAlbum Geo 手动标签调整说明

## 手动调整某个 stop 的 labelOffset

当前优先使用自动避让。若要手动微调，可在 stop 数据中增加：

```json
{
  "order": 9,
  "name": "泸沽湖",
  "labelOffset": { "x": 18, "y": -12 }
}
```

后续可在 `scripts/route_projection.py` 的 label placement 阶段读取该字段，把自动计算后的 `labelX / labelY` 加上偏移量。

## 手动隐藏某个 label

可在 stop 中增加：

```json
{
  "order": 12,
  "hideLabel": true
}
```

后续可在 `_select_label_indexes()` 中跳过 `hideLabel=true` 的点位。marker 仍会显示编号，完整名称保留在页面 timeline。

## 调整 mapPadding / 绘图区

当前绘图区在 `scripts/route_projection.py`：

```python
left = 72
right = width - 72
top = 80
bottom = height - 160
```

也可以在调用 `computeRouteLayout(stops, width, height, options)` 时传入：

```python
{"mapPadding": {"left": 88, "right": 88, "top": 88, "bottom": 150}}
```

如果路线仍贴边，可增大左右边距；如果地图主视觉太扁，可适当减少 `bottom` 的预留空间或调高 SVG 高度。

## 调整 timeline 展示数量

页面 timeline 在 `demo-site/app.js` 的 `renderRouteTimeline()` 中控制：

```js
const visible = expanded ? stops : stops.slice(0, 8);
```

将 `8` 改成其他数字即可调整默认展示数量。timeline 位于地图卡片下方，不再覆盖 SVG 主视觉。
