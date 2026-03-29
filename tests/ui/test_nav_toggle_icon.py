import sys

import pytest
from PySide6.QtWidgets import QApplication

from markitdowngui.ui.nav_toggle_icon import make_nav_menu_toggle_icon, nav_menu_toggle_stroke_hex


@pytest.fixture
def qt_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_nav_menu_toggle_stroke_hex():
    assert nav_menu_toggle_stroke_hex("light") == "#2B3F45"
    assert nav_menu_toggle_stroke_hex("dark") == "#ECEFF4"
    assert nav_menu_toggle_stroke_hex("perfect_dark") == "#ECEFF4"


def test_make_nav_menu_toggle_icon_valid(qt_app):
    icon = make_nav_menu_toggle_icon("dark")
    assert not icon.isNull()
