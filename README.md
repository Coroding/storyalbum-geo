# StoryAlbum Geo

StoryAlbum Geo is a photo-GPS travel memory album generator. It reads EXIF GPS from local photos, enriches stops with AMap reverse geocoding in Python, caches a static route map, and renders a local showcase page.

## What It Shows

- EXIF photo scan and GPS manifest.
- Time-sorted route stops grouped from nearby photos.
- AMap reverse geocode enrichment with local cache.
- Cached AMap static map plus a stylized album route map.
- A static `demo-site/index.html` showcase with route cards and photo wall.

## Stylized Route Projection

`scripts/stylize_geo_route.py` uses `scripts/route_projection.py` to build the Album Style map from real stop coordinates in `assets/geo_album/meta/geo_stops_enriched.json`.

- `coordinate-based`: uses EXIF/GPS stop coordinates and local projection.
- `cached-based`: reserved for cached geocode or marker coordinates.
- `order-based fallback`: used only when coordinates are missing, and marked as estimated.

The stylized map preserves relative point direction and route order for album display. It is not an exact navigation route and does not make any frontend AMap API request.

## API Key

Create `.env.local` in the project root:

```env
AMAP_WEB_SERVICE_KEY=your_key_here
```

Do not commit `.env.local`, `.env.local.example`, key files, or secret JSON files.

## Run

```bash
python scripts/scan_geo_photos.py
python scripts/extract_geo_exif.py
python scripts/build_geo_stops.py
python scripts/amap_reverse_geocode.py --dry-run --max-calls 50
python scripts/amap_reverse_geocode.py --max-calls 50
python scripts/amap_static_map.py --dry-run
python scripts/amap_static_map.py
python scripts/stylize_geo_route.py
python scripts/build_geo_album_config.py
python scripts/validate_geo_album.py
```

Open `demo-site/index.html` directly.

## Deploy To Vercel

Use the repository root as the Vercel root directory. The root `index.html` redirects to `demo-site/`, and all page images are bundled under `demo-site/assets/geo_album/`.

## Notes

Photos usually store WGS84 GPS coordinates, while AMap uses GCJ-02. This MVP records that offset risk and can be upgraded with coordinate conversion or route planning APIs.
