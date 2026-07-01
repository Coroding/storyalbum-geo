import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.route_projection import (
    LABEL_LIMIT,
    VIEWBOX_HEIGHT,
    VIEWBOX_WIDTH,
    computeRouteLayout,
    project_route_stops,
    renderAlbumRouteSvg,
)


class RouteProjectionTests(unittest.TestCase):
    def test_projects_coordinates_inside_viewbox_and_preserves_direction(self):
        stops = [
            {"order": 1, "name": "丽江", "centroid_wgs84": {"lng": 100.20, "lat": 26.90}},
            {"order": 2, "name": "中途点", "centroid_wgs84": {"lng": 100.50, "lat": 27.20}},
            {"order": 3, "name": "泸沽湖", "centroid_wgs84": {"lng": 100.85, "lat": 27.70}},
        ]

        projection = project_route_stops(stops)
        points = projection["points"]

        for point in points:
            self.assertGreaterEqual(point["x"], 0)
            self.assertLessEqual(point["x"], VIEWBOX_WIDTH)
            self.assertGreaterEqual(point["y"], 0)
            self.assertLessEqual(point["y"], VIEWBOX_HEIGHT)

        self.assertLess(points[0]["x"], points[2]["x"], "更东的点应有更大的 x")
        self.assertGreater(points[0]["y"], points[2]["y"], "更北的点应有更小的 y")
        self.assertEqual(projection["mode"], "coordinate-based")
        self.assertGreaterEqual(projection["turnaround_index"], 1)

    def test_label_rules_keep_start_end_and_limit_visible_labels(self):
        stops = []
        for index in range(12):
            stops.append(
                {
                    "order": index + 1,
                    "name": f"普通点{index + 1}",
                    "centroid_wgs84": {"lng": 100.2 + index * 0.04, "lat": 26.9 + index * 0.05},
                    "photos": [{} for _ in range(index % 4)],
                }
            )
        stops[0]["name"] = "丽江古城"
        stops[-1]["name"] = "泸沽湖国家级风景区"

        projection = project_route_stops(stops)
        visible = [point for point in projection["points"] if point["show_label"]]

        self.assertLessEqual(len(visible), LABEL_LIMIT)
        self.assertTrue(projection["points"][0]["show_label"])
        self.assertTrue(projection["points"][-1]["show_label"])
        self.assertEqual(projection["hidden_label_count"], len(stops) - len(visible))

    def test_missing_coordinates_use_order_based_fallback(self):
        projection = project_route_stops(
            [
                {"order": 1, "name": "无坐标起点"},
                {"order": 2, "name": "无坐标终点"},
            ]
        )

        self.assertEqual(projection["mode"], "order-based fallback")
        self.assertTrue(all(point["confidence"] == "fallback" for point in projection["points"]))

    def test_compute_route_layout_keeps_points_out_of_legend_area(self):
        stops = [
            {"order": 1, "name": "丽江", "centroid_wgs84": {"lng": 100.20, "lat": 26.90}},
            {"order": 2, "name": "树底", "centroid_wgs84": {"lng": 100.43, "lat": 26.99}},
            {"order": 3, "name": "泸沽湖", "centroid_wgs84": {"lng": 100.85, "lat": 27.70}},
            {"order": 4, "name": "丽江市博物院", "centroid_wgs84": {"lng": 100.23, "lat": 26.88}},
        ]

        layout = computeRouteLayout(stops, VIEWBOX_WIDTH, VIEWBOX_HEIGHT)
        map_area = layout["mapArea"]

        self.assertIn("routePath", layout)
        self.assertEqual(layout["mode"], "coordinate-based")
        for point in layout["points"]:
            self.assertGreaterEqual(point["x"], map_area["left"])
            self.assertLessEqual(point["x"], map_area["right"])
            self.assertGreaterEqual(point["y"], map_area["top"])
            self.assertLessEqual(point["y"], map_area["bottom"])
        self.assertLessEqual(layout["labelCount"], 6)

    def test_render_album_route_svg_has_no_embedded_timeline(self):
        layout = computeRouteLayout(
            [
                {"order": 1, "name": "丽江", "centroid_wgs84": {"lng": 100.20, "lat": 26.90}},
                {"order": 2, "name": "泸沽湖", "centroid_wgs84": {"lng": 100.85, "lat": 27.70}},
            ],
            VIEWBOX_WIDTH,
            VIEWBOX_HEIGHT,
        )

        svg = renderAlbumRouteSvg(layout)

        self.assertIn('viewBox="0 0 1000 680"', svg)
        self.assertIn("路线示意 / 非导航路线", svg)
        self.assertNotIn("完整停靠点 timeline", svg)


if __name__ == "__main__":
    unittest.main()
