from __future__ import annotations

import shutil
from pathlib import Path

from geo_album_utils import PROJECT_ROOT, SOURCE_DIR, SUPPORTED_EXTENSIONS, ensure_geo_dirs


RAW_INPUT_DIR = PROJECT_ROOT / "带地理信息图片"


def main() -> None:
    ensure_geo_dirs()
    copied = 0
    skipped = 0
    for source in sorted(RAW_INPUT_DIR.iterdir()):
        if not source.is_file() or source.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        target = SOURCE_DIR / source.name
        if target.exists():
            skipped += 1
            continue
        shutil.copy2(source, target)
        copied += 1
    total = len([p for p in SOURCE_DIR.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS])
    print(f"source={RAW_INPUT_DIR}")
    print(f"target={SOURCE_DIR}")
    print(f"copied={copied}")
    print(f"skipped_existing={skipped}")
    print(f"target_total={total}")


if __name__ == "__main__":
    main()

