"""Custom navigation menu (hamburger) icon: loop / infinity mark instead of Fluent MENU bars.

The path is adapted from the Lucide ``infinity`` icon (ISC License, https://lucide.dev/license).
Rendered via ``QSvgRenderer`` so stroke color matches light vs dark chrome.
"""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


def _svg_bytes(stroke_hex: str) -> QByteArray:
    # Slightly thinner stroke than default Lucide 2px for 16–24px nav slots.
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
        f'<path stroke="{stroke_hex}" stroke-width="1.85" stroke-linecap="round" '
        'stroke-linejoin="round" '
        'd="M12 12c-2-2.67-4-4-6-4a4.5 4.5 0 0 0 0 9c2 0 4-1.33 6-4zm0 0c2 2.67 4 4 6 4a4.5 4.5 0 0 0 0-9c-2 0-4 1.33-6 4z"/>'
        "</svg>"
    )
    return QByteArray(svg.encode("utf-8"))


def nav_menu_toggle_stroke_hex(theme_key: str) -> str:
    """Stroke color for the nav rail (matches caption / nav label contrast)."""
    if theme_key == "light":
        return "#2B3F45"
    return "#ECEFF4"


def make_nav_menu_toggle_icon(theme_key: str) -> QIcon:
    stroke = nav_menu_toggle_stroke_hex(theme_key)
    data = _svg_bytes(stroke)
    renderer = QSvgRenderer(data)
    if not renderer.isValid():
        return QIcon()
    icon = QIcon()
    for size in (48, 64, 96, 128):
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()
        icon.addPixmap(pm)
    return icon
