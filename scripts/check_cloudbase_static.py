from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SITE_DIR = ROOT / "demo-site"
FORBIDDEN_PATTERNS = [
    re.compile(r"(?<![A-Za-z0-9])[0-9a-f]{32}(?![A-Za-z0-9])", re.IGNORECASE),
    re.compile(r"AMAP_WEB_SERVICE_KEY"),
    re.compile(r"key=(?!\*\*\*)[^&\s\"']+", re.IGNORECASE),
]


def _iter_text_files(site_dir: Path) -> Iterable[Path]:
    suffixes = {".html", ".css", ".js", ".json", ".txt", ".svg"}
    for path in site_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in suffixes:
            yield path


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _asset_exists(site_dir: Path, relative_path: str, label: str, problems: list[str]) -> None:
    if not relative_path:
        problems.append(f"{label}: missing path")
        return
    if relative_path.startswith(("http://", "https://", "/")):
        problems.append(f"{label}: path must be local relative for CloudBase subpath deploy: {relative_path}")
        return
    if relative_path.startswith("../"):
        problems.append(f"{label}: path escapes demo-site deploy root: {relative_path}")
        return
    if not (site_dir / relative_path).exists():
        problems.append(f"{label}: file not found: {relative_path}")


def check_static_site(site_dir: Path) -> list[str]:
    problems: list[str] = []
    index = site_dir / "index.html"
    app_js = site_dir / "app.js"
    data_json = site_dir / "data" / "geo_album.json"
    data_js = site_dir / "data" / "geo_album.js"

    for required in [index, app_js, data_json, data_js]:
        if not required.exists():
            problems.append(f"required file missing: {required.relative_to(ROOT)}")

    if problems:
        return problems

    html = index.read_text(encoding="utf-8")
    app = app_js.read_text(encoding="utf-8")
    if 'src="data/geo_album.js"' not in html:
        problems.append("index.html must load data/geo_album.js before app.js for local fallback data")
    if 'const DATA_URL = "data/geo_album.json"' not in app:
        problems.append("app.js must keep local JSON as its primary data URL")
    if "window.STORYALBUM_GEO_DATA" not in app:
        problems.append("app.js must support the inline/local JS data fallback")
    if "restapi.amap.com" in html + app:
        problems.append("front end must not request AMap API directly")

    album = _read_json(data_json)
    _asset_exists(site_dir, album.get("cover", ""), "cover", problems)

    route_map = album.get("map", {})
    _asset_exists(site_dir, route_map.get("amapStatic", ""), "amap static map", problems)
    _asset_exists(site_dir, route_map.get("fallback", ""), "styled fallback SVG", problems)
    _asset_exists(site_dir, route_map.get("fallbackPng", ""), "styled fallback PNG", problems)
    _asset_exists(site_dir, route_map.get("projectionMetadata", ""), "projection metadata", problems)

    if not album.get("stops"):
        problems.append("album data must include stops")
    if not album.get("photos"):
        problems.append("album data must include photo wall items")

    for index_, stop in enumerate(album.get("stops", []), start=1):
        if "coordinate" not in stop:
            problems.append(f"stop {index_}: missing coordinate for relative route projection")
        for photo_index, photo in enumerate(stop.get("photos", []), start=1):
            _asset_exists(site_dir, photo.get("src", ""), f"stop {index_} photo {photo_index}", problems)

    for index_, photo in enumerate(album.get("photos", []), start=1):
        _asset_exists(site_dir, photo.get("src", ""), f"photo wall item {index_}", problems)

    for text_file in _iter_text_files(site_dir):
        text = text_file.read_text(encoding="utf-8", errors="ignore")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(text):
                problems.append(f"forbidden secret-like value in {text_file.relative_to(ROOT)}")
                break

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate StoryAlbum Geo static files before CloudBase deploy.")
    parser.add_argument("--site-dir", default=str(DEFAULT_SITE_DIR), help="Static site directory to deploy.")
    args = parser.parse_args()

    site_dir = Path(args.site_dir).resolve()
    problems = check_static_site(site_dir)
    if problems:
        print("CloudBase static deploy check failed:")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print(f"CloudBase static deploy check passed: {site_dir}")
    print("deploy_dir=demo-site")
    print("deploy_path=/storyalbum-geo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
