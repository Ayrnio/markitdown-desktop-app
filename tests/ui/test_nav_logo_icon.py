import sys

import pytest
from PySide6.QtWidgets import QApplication

from markitdowngui.resource_paths import ayrn_nav_logo_path
from markitdowngui.ui.nav_logo_icon import make_ayrn_nav_return_icon


@pytest.fixture
def qt_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_ayrn_nav_logo_packaged():
    assert ayrn_nav_logo_path().is_file()


def test_make_ayrn_nav_return_icon_valid(qt_app):
    icon = make_ayrn_nav_return_icon()
    assert not icon.isNull()
