"""AYRN brand logo for the navigation return (back) button."""

from __future__ import annotations

from collections import deque

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPixmap

from markitdowngui.resource_paths import ayrn_nav_logo_path


def _is_dark_matte(c: QColor, rgb_max: int) -> bool:
    return (
        c.alpha() > 40
        and c.red() <= rgb_max
        and c.green() <= rgb_max
        and c.blue() <= rgb_max
    )


def _flood_edge_dark_to_transparent(img: QImage, rgb_max: int = 42) -> QImage:
    """Remove connected near-black regions touching image edges (common fake 'matte')."""
    w, h = img.width(), img.height()
    if w < 3 or h < 3:
        return img
    out = img.copy()
    seen = [[False] * w for _ in range(h)]
    q: deque[tuple[int, int]] = deque()

    for x in range(w):
        for y in (0, h - 1):
            if _is_dark_matte(out.pixelColor(x, y), rgb_max):
                seen[y][x] = True
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if not seen[y][x] and _is_dark_matte(out.pixelColor(x, y), rgb_max):
                seen[y][x] = True
                q.append((x, y))

    while q:
        x, y = q.popleft()
        c = out.pixelColor(x, y)
        c.setAlpha(0)
        out.setPixelColor(x, y, c)
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx]:
                if _is_dark_matte(out.pixelColor(nx, ny), rgb_max):
                    seen[ny][nx] = True
                    q.append((nx, ny))
    return out


def _prepare_logo_image(path_str: str) -> QImage:
    img = QImage(path_str)
    if img.isNull():
        return img
    img = img.convertToFormat(QImage.Format.Format_ARGB32)
    # If corners look like a black matte, peel it without touching interior blues.
    corners = [
        img.pixelColor(0, 0),
        img.pixelColor(img.width() - 1, 0),
        img.pixelColor(0, img.height() - 1),
        img.pixelColor(img.width() - 1, img.height() - 1),
    ]
    if corners and all(
        c.alpha() > 200 and c.red() < 55 and c.green() < 55 and c.blue() < 55
        for c in corners
    ):
        img = _flood_edge_dark_to_transparent(img)
    return img


def make_ayrn_nav_return_icon() -> QIcon:
    """High-DPI icon; uses QImage scaling to preserve alpha better than raw QPixmap.scaled."""
    path = ayrn_nav_logo_path()
    if not path.is_file():
        return QIcon()
    img = _prepare_logo_image(str(path))
    if img.isNull():
        return QIcon()
    icon = QIcon()
    for size in (32, 48, 64, 96, 128, 160):
        scaled = img.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        pm = QPixmap.fromImage(scaled)
        if not pm.isNull():
            icon.addPixmap(pm)
    return icon
