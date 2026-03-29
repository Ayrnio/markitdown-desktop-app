"""Version label + sparkle icon for the caption strip (AnythingLLM-style)."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from markitdowngui.version_info import get_app_version

# Muted amber / gold (readable on dark title bars; darker variant for light).
_AMBER_DARK_BG = QColor(209, 172, 92)
_AMBER_LIGHT_BG = QColor(166, 116, 40)


def _sparkle_pixmap(size: int, color: QColor) -> QPixmap:
    """Small four-ray sparkle (two crossed strokes), similar to common app badges."""
    d = max(size, 8)
    pm = QPixmap(d, d)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    cx = cy = d / 2.0
    r = d * 0.38
    pen = QPen(color)
    pen.setWidthF(max(1.15, d / 11))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    for deg in (0.0, 45.0):
        rad = math.radians(deg)
        c, s = math.cos(rad), math.sin(rad)
        p.drawLine(
            QPointF(cx + r * c, cy + r * s),
            QPointF(cx - r * c, cy - r * s),
        )
    p.end()
    return pm


class TitleBarVersionBadge(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._icon = QLabel(self)
        self._icon.setFixedSize(14, 14)
        self._icon.setScaledContents(True)

        self._text = QLabel(self)
        self._text.setText(f"v{get_app_version()}")
        f = self._text.font()
        f.setPointSize(10)
        self._text.setFont(f)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 14, 0)
        lay.setSpacing(6)
        lay.addWidget(self._icon, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self._text, 0, Qt.AlignmentFlag.AlignVCenter)

    def apply_theme(self, *, theme_key: str) -> None:
        if theme_key == "light":
            c = _AMBER_LIGHT_BG
        else:
            c = _AMBER_DARK_BG
        self._icon.setPixmap(_sparkle_pixmap(14, c))
        self._text.setStyleSheet(f"color: {c.name()}; background: transparent;")


def title_bar_buttons_column_index(title_bar) -> int:
    """Index of ``FluentTitleBar``'s ``vBoxLayout`` in ``hBoxLayout``."""
    lay = title_bar.hBoxLayout
    vb = title_bar.vBoxLayout
    for i in range(lay.count()):
        item = lay.itemAt(i)
        if item is not None and item.layout() is vb:
            return i
    return lay.count() - 1


def install_title_bar_version_badge(title_bar) -> TitleBarVersionBadge:
    lay = title_bar.hBoxLayout
    idx = title_bar_buttons_column_index(title_bar)
    lay.insertStretch(idx, 1)
    badge = TitleBarVersionBadge(parent=title_bar)
    lay.insertWidget(
        idx + 1,
        badge,
        0,
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
    )
    return badge
