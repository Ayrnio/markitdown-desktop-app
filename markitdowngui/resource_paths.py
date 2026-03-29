"""Resolve packaged resource files in development and PyInstaller builds."""

from __future__ import annotations

import sys
from pathlib import Path

_LOGO_NAME = "ayrn_nav_logo.png"


def package_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "markitdowngui"
    return Path(__file__).resolve().parent


def resource_path(filename: str) -> Path:
    return package_root() / "resources" / filename


def ayrn_nav_logo_path() -> Path:
    return resource_path(_LOGO_NAME)
