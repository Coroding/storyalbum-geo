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
        self.assertIn("renderMapComparison", js)
        self.assertIn("原始高德地图底图", js)
        self.assertIn("风格化路线图", js)

    def test_geo_data_uses_deployable_local_asset_paths_and_utf8_copy(self):
        data = (ROOT / "demo-site" / "data" / "geo_album.json").read_text(encoding="utf-8")

        self.assertIn('"cover": "assets/geo_album/source_photos/selected/', data)
        self.assertIn('"amapStatic": "assets/geo_album/maps/amap/geo_route_amap.png"', data)
        self.assertNotIn("../assets/", data)
        self.assertNotIn("鎴", data)
        self.assertNotIn("鍦", data)


if __name__ == "__main__":
    unittest.main()
