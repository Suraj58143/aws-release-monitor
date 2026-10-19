"""Assemble the static dashboard and its current dataset for Pages."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = ROOT / "site"


def build_site() -> None:
    dashboard_dir = ROOT / "dashboard"
    data_dir = ROOT / "data"
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True)
    for path in dashboard_dir.iterdir():
        if path.is_file():
            shutil.copy2(path, SITE_DIR / path.name)
    shutil.copytree(data_dir, SITE_DIR / "data")


if __name__ == "__main__":
    build_site()
