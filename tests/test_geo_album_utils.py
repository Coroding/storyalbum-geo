import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.geo_album_utils import (
    cluster_photo_records,
    mask_amap_key,
    pick_stop_name,
    relative_to_demo,
)


class GeoAlbumUtilsTest(unittest.TestCase):
    def test_mask_amap_key_hides_query_value(self):
        url = "https://restapi.amap.com/v3/geocode/regeo?location=1,2&key=secret-key&output=json"

        self.assertNotIn("secret-key", mask_amap_key(url))
        self.assertIn("key=***", mask_amap_key(url))

    def test_cluster_photo_records_groups_nearby_consecutive_photos(self):
        photos = [
            {
                "filename": "a.jpg",
                "relative_path": "assets/geo_album/source_photos/original/a.jpg",
                "datetime_original": "2026:01:01 10:00:00",
                "gps_lat_wgs84": 30.0,
                "gps_lng_wgs84": 120.0,
                "has_gps": True,
            },
            {
                "filename": "b.jpg",
                "relative_path": "assets/geo_album/source_photos/original/b.jpg",
                "datetime_original": "2026:01:01 10:01:00",
                "gps_lat_wgs84": 30.0005,
                "gps_lng_wgs84": 120.0005,
                "has_gps": True,
            },
            {
                "filename": "c.jpg",
                "relative_path": "assets/geo_album/source_photos/original/c.jpg",
                "datetime_original": "2026:01:01 11:00:00",
                "gps_lat_wgs84": 31.0,
                "gps_lng_wgs84": 121.0,
                "has_gps": True,
            },
        ]

        stops = cluster_photo_records(photos, threshold_m=200)

        self.assertEqual(len(stops), 2)
        self.assertEqual([p["filename"] for p in stops[0]["photos"]], ["a.jpg", "b.jpg"])
        self.assertEqual(stops[0]["caption"], "第一站：旅程开始")
        self.assertEqual(stops[1]["caption"], "最后一站：路线收尾")

    def test_pick_stop_name_prefers_nearest_poi_then_aoi_then_admin(self):
        regeocode = {
            "formatted_address": "浙江省杭州市西湖区某地",
            "addressComponent": {"township": "西溪街道", "district": "西湖区"},
            "pois": [{"name": "最近咖啡店"}],
            "aois": [{"name": "西溪湿地"}],
        }

        self.assertEqual(pick_stop_name(regeocode, fallback="地点 01"), "最近咖啡店")

        regeocode["pois"] = []
        self.assertEqual(pick_stop_name(regeocode, fallback="地点 01"), "西溪湿地")

        regeocode["aois"] = []
        self.assertEqual(pick_stop_name(regeocode, fallback="地点 01"), "西溪街道")

    def test_relative_to_demo_uses_forward_slashes(self):
        project_root = Path("E:/W-项目学习/AI视频剪辑")
        path = project_root / "assets" / "geo_album" / "maps" / "styled" / "cute_geo_route.svg"

        self.assertEqual(
            relative_to_demo(path, project_root),
            "../assets/geo_album/maps/styled/cute_geo_route.svg",
        )


if __name__ == "__main__":
    unittest.main()
