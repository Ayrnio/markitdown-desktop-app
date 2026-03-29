"""Larger icon rect for the nav return button (qfluentwidgets uses a fixed 16×16 draw box)."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QCursor, QPainter

from qfluentwidgets.common.color import autoFallbackThemeColor
from qfluentwidgets.common.config import isDarkTheme
from qfluentwidgets.common.icon import drawIcon

# NavigationToolButton is 40×36; default library icon rect is 16×16 — too small for a brand mark.
_ICON_PX = 28


def paint_navigation_return_button_large_icon(self, e) -> None:
    """Bound as ``types.MethodType(..., returnButton)`` — mirrors ``NavigationPushButton.paintEvent``."""
    painter = QPainter(self)
    painter.setRenderHints(
        QPainter.RenderHint.Antialiasing
        | QPainter.RenderHint.TextAntialiasing
        | QPainter.RenderHint.SmoothPixmapTransform,
    )
    painter.setPen(Qt.PenStyle.NoPen)

    if self.isPressed:
        painter.setOpacity(0.7)
    if not self.isEnabled():
        painter.setOpacity(0.4)

    c = 255 if isDarkTheme() else 0
    global_rect = QRect(self.mapToGlobal(QPoint()), self.size())

    if self._canDrawIndicator():
        painter.setBrush(QColor(c, c, c, 6 if self.isEnter else 10))
        painter.drawRoundedRect(self.rect(), 5, 5)
        painter.setBrush(
            autoFallbackThemeColor(self.lightIndicatorColor, self.darkIndicatorColor)
        )
        painter.drawRoundedRect(self.indicatorRect(), 1.5, 1.5)
    elif (
        (self.isEnter and global_rect.contains(QCursor.pos())) or self.isAboutSelected
    ) and self.isEnabled():
        painter.setBrush(QColor(c, c, c, 6 if self.isAboutSelected else 10))
        painter.drawRoundedRect(self.rect(), 5, 5)

    iw = ih = _ICON_PX
    x = (self.width() - iw) / 2
    y = (self.height() - ih) / 2
    drawIcon(self._icon, painter, QRectF(x, y, iw, ih))


def patch_nav_return_button_large_icon(return_button) -> None:
    import types

    return_button.paintEvent = types.MethodType(
        paint_navigation_return_button_large_icon, return_button
    )
