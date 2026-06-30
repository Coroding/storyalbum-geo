from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image

from geo_album_utils import META_DIR, PROJECT_ROOT, SOURCE_DIR, SUPPORTED_EXTENSIONS, ensure_geo_dirs, posix_rel, write_csv, write_json


FIELDNAMES = [
    "filename",
    "relative_path",
    "width",
    "height",
    "datetime_original",
    "gps_lat_wgs84",
    "gps_lng_wgs84",
    "gps_altitude",
    "has_gps",
    "exif_status",
    "selected",
    "notes",
    "sort_time",
]

GPS_TAGS = {value: key for key, value in ExifTags.GPSTAGS.items()}


def _ratio_to_float(value: Any) -> float:
    if isinstance(value, Fraction):
        return float(value)
    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        return float(value.numerator) / float(value.denominator)
    if isinstance(value, tuple) and len(value) == 2:
        return float(value[0]) / float(value[1])
    return float(value)


def _dms_to_decimal(values: Any, ref: str) -> float:
    degrees = _ratio_to_float(values[0])
    minutes = _ratio_to_float(values[1])
    seconds = _ratio_to_float(values[2])
    decimal = degrees + minutes / 60 + seconds / 3600
    if ref in ("S", "W"):
        decimal *= -1
    return round(decimal, 8)


def _datetime_from_filename(path: Path) -> str:
    text = path.stem
    for fmt in ("%Y%m%d_%H%M%S",):
        try:
            match = __import__("re").search(r"(\d{8}_\d{6})", text)
            if match:
                return datetime.strptime(match.group(1), fmt).strftime("%Y:%m:%d %H:%M:%S")
        except ValueError:
            pass
    return ""


def _read_with_pillow(path: Path) -> dict[str, Any]:
    row: dict[str, Any] = {
        "filename": path.name,
        "relative_path": posix_rel(path),
        "width": "",
        "height": "",
        "datetime_original": "",
        "gps_lat_wgs84": "",
        "gps_lng_wgs84": "",
        "gps_altitude": "",
        "has_gps": False,
        "exif_status": "not_read",
        "selected": False,
        "notes": "",
        "sort_time": "",
    }
    try:
        with Image.open(path) as image:
            row["width"], row["height"] = image.size
            exif = image.getexif()
            if not exif:
                row["exif_status"] = "no_exif"
            else:
                row["exif_status"] = "ok"
                row["datetime_original"] = exif.get(36867) or exif.get(306) or ""
                gps_ifd = exif.get_ifd(34853) if 34853 in exif else {}
                if gps_ifd:
                    lat_values = gps_ifd.get(GPS_TAGS["GPSLatitude"])
                    lat_ref = gps_ifd.get(GPS_TAGS["GPSLatitudeRef"], "N")
                    lng_values = gps_ifd.get(GPS_TAGS["GPSLongitude"])
                    lng_ref = gps_ifd.get(GPS_TAGS["GPSLongitudeRef"], "E")
                    if lat_values and lng_values:
                        row["gps_lat_wgs84"] = _dms_to_decimal(lat_values, lat_ref)
                        row["gps_lng_wgs84"] = _dms_to_decimal(lng_values, lng_ref)
                        row["has_gps"] = True
                        row["selected"] = True
                    altitude = gps_ifd.get(GPS_TAGS.get("GPSAltitude"))
                    if altitude is not None:
                        row["gps_altitude"] = round(_ratio_to_float(altitude), 2)
    except Exception as exc:
        row["exif_status"] = "error"
        row["notes"] = f"{type(exc).__name__}: {exc}"

    if not row["datetime_original"]:
        filename_time = _datetime_from_filename(path)
        if filename_time:
            row["datetime_original"] = filename_time
            row["notes"] = (row["notes"] + "; " if row["notes"] else "") + "datetime from filename"
        else:
            stat_time = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y:%m:%d %H:%M:%S")
            row["sort_time"] = stat_time
            row["notes"] = (row["notes"] + "; " if row["notes"] else "") + "sort by file modified time"
    return row


def _exiftool_available() -> bool:
    return bool(shutil.which("exiftool"))


def main() -> None:
    ensure_geo_dirs()
    if _exiftool_available():
        print("exiftool detected; Pillow reader is still used for portable MVP fields.")
    rows = [_read_with_pillow(path) for path in sorted(SOURCE_DIR.iterdir()) if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS]
    rows.sort(key=lambda row: (row.get("datetime_original") or row.get("sort_time") or "", row.get("filename") or ""))
    write_csv(META_DIR / "photo_manifest.csv", rows, FIELDNAMES)
    write_json(META_DIR / "photo_manifest.json", rows)

    total = len(rows)
    gps_count = sum(1 for row in rows if row.get("has_gps"))
    time_count = sum(1 for row in rows if row.get("datetime_original"))
    print(f"total_images={total}")
    print(f"gps_images={gps_count}")
    print(f"non_gps_images={total - gps_count}")
    print(f"datetime_images={time_count}")
    print(f"missing_datetime_images={total - time_count}")


if __name__ == "__main__":
    main()

