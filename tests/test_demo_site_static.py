import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DemoSiteStaticTest(unittest.TestCase):
    def test_geo_page_uses_lake_palette_and_dual_map_layout(self):
        html = (ROOT / "demo-site" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "demo-site" / "styles.css").read_text(encoding="utf-8")
        js = (ROOT / "demo-site" / "app.js").read_text(encoding="utf-8")

        self.assertIn("StoryAlbum Geo｜基于照片地址的旅行回忆相册", html)
        self.assertIn("--lake-blue-deep: #3772BE", css)
        self.assertIn("--cream-yellow: #F1EABD", css)
        self.assertIn('id="amapRouteMap"', html)
        self.assertIn('id="styledRouteMap"', html)
        self.assertIn("基于真实点位相对位置", html)
        self.assertIn("不是精确导航路线", html)
        self.assertIn('id="projectionDebug"', html)
        self.assertIn('id="routeTimeline"', html)
        self.assertIn("renderMapComparison", js)
        self.assertIn("renderProjectionDebug", js)
        self.assertIn("renderRouteTimeline", js)
        self.assertIn("原始高德地图底图", js)
        self.assertIn("风格化路线图", js)
        self.assertNotIn("restapi.amap.com", js)
        self.assertNotRegex(html + js, r"(?i)(?<![A-Za-z0-9])[0-9a-f]{32}(?![A-Za-z0-9])")

    def test_geo_data_uses_deployable_local_asset_paths_and_utf8_copy(self):
        data = (ROOT / "demo-site" / "data" / "geo_album.json").read_text(encoding="utf-8")

        self.assertIn('"cover": "assets/geo_album/source_photos/selected/', data)
        self.assertIn('"amapStatic": "assets/geo_album/maps/amap/geo_route_amap.png"', data)
        self.assertIn('"projectionMetadata": "assets/geo_album/maps/styled/cute_geo_route_projection.json"', data)
        self.assertIn("基于真实点位相对位置", data)
        self.assertIn("不是精确导航路线", data)
        self.assertNotIn("../assets/", data)
        self.assertNotIn("鎴", data)
        self.assertNotIn("鍦", data)

    def test_styled_route_svg_uses_projected_album_map_rules(self):
        svg = (ROOT / "assets" / "geo_album" / "maps" / "styled" / "cute_geo_route.svg").read_text(encoding="utf-8")

        self.assertIn('viewBox="0 0 1000 680"', svg)
        self.assertIn("基于真实点位相对位置", svg)
        self.assertIn("不是精确导航路线", svg)
        self.assertIn("风格化地图用于旅行相册展示", svg)
        self.assertNotIn("完整停靠点 timeline", svg)
        self.assertNotIn("restapi.amap.com", svg)


if __name__ == "__main__":
    unittest.main()
