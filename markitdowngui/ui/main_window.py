from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication, QResizeEvent, QShowEvent
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

from qfluentwidgets import FluentIcon as FIF, FluentWindow, NavigationItemPosition
from qfluentwidgets.common.style_sheet import setCustomStyleSheet

from markitdowngui.core.settings import SettingsManager
from markitdowngui.ui.dialogs.about import AboutDialog
from markitdowngui.ui.help_interface import HelpInterface
from markitdowngui.ui.home_interface import HomeInterface
from markitdowngui.ui.settings_interface import SettingsInterface
from markitdowngui.ui.nav_toggle_icon import make_nav_menu_toggle_icon
from markitdowngui.ui.themes import apply_app_theme, build_app_stylesheet
from markitdowngui.utils.logger import AppLogger
from markitdowngui.utils.translations import DEFAULT_LANG, get_translation

# Home, Settings, and Help share the same centered column width (readable on 21:9).
_MAIN_COLUMN_MAX_WIDTH_PX = 1240
# Fallback when host width not laid out yet: subtract from window width for the main column.
_NAV_AND_CHROME_RESERVE_PX = 300
_MAIN_CONTENT_HORIZONTAL_GUTTER_PX = 24


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        # expand() must not run during __init__: qfluentwidgets' indicator cleanup calls
        # _findIndicatorItem(), which returns None until nav widgets are visible (after show).
        self._did_schedule_initial_nav_expand = False
        self._install_max_width_content_shell()
        self.settings_manager = SettingsManager()

        self._init_window()
        self._init_interfaces()
        self._init_navigation()
        self.apply_theme()

        AppLogger.info("MainWindow initialized with FluentWindow")

    def _install_max_width_content_shell(self) -> None:
        """Center stacked pages in a max-width column so layouts stay readable on wide monitors."""
        stacked = self.stackedWidget
        self.widgetLayout.removeWidget(stacked)

        host = QWidget(self)
        host.setObjectName("mainContentMaxWidthHost")
        self._main_content_host = host
        host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        host_lay = QHBoxLayout(host)
        host_lay.setContentsMargins(0, 0, 0, 0)
        host_lay.setSpacing(0)
        host_lay.addStretch(1)

        cap = QWidget(host)
        cap.setObjectName("mainContentMaxWidthCap")
        self._main_content_cap = cap
        self._pin_content_cap_width(_MAIN_COLUMN_MAX_WIDTH_PX)
        cap.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Expanding,
        )

        cap_lay = QVBoxLayout(cap)
        cap_lay.setContentsMargins(
            _MAIN_CONTENT_HORIZONTAL_GUTTER_PX,
            0,
            _MAIN_CONTENT_HORIZONTAL_GUTTER_PX,
            0,
        )
        cap_lay.setSpacing(0)
        cap_lay.addWidget(stacked, 1)

        # Stretch so side gutters share extra space; width is driven by _pin_content_cap_width, not sizeHint.
        host_lay.addWidget(cap, 1, Qt.AlignmentFlag.AlignHCenter)
        host_lay.addStretch(1)

        self.widgetLayout.addWidget(host)

    def _init_window(self) -> None:
        self.setWindowTitle(self.translate("app_title"))
        self.resize(980, 740)
        self.setMinimumSize(820, 520)

        geometry = self.settings_manager.get_window_geometry()
        if geometry:
            self.restoreGeometry(geometry)

    def _init_interfaces(self) -> None:
        self.homeInterface = HomeInterface(self.settings_manager, self)
        self.settingsInterface = SettingsInterface(
            self.settings_manager, self.translate, self
        )
        self.helpInterface = HelpInterface(self.translate, self)

        self.settingsInterface.theme_mode_changed.connect(self._on_theme_mode_changed)
        self.helpInterface.check_updates_requested.connect(
            self.homeInterface.manual_update_check
        )
        self.helpInterface.show_shortcuts_requested.connect(
            self.homeInterface.show_shortcuts
        )
        self.helpInterface.show_about_requested.connect(self.show_about)

    def _init_navigation(self) -> None:
        self.addSubInterface(
            self.homeInterface, FIF.HOME, self.translate("nav_home")
        )
        self.addSubInterface(
            self.settingsInterface, FIF.SETTING, self.translate("nav_settings")
        )
        self.addSubInterface(self.helpInterface, FIF.HELP, self.translate("nav_help"))

        self.navigationInterface.addSeparator()
        self.navigationInterface.addItem(
            routeKey="convert_action",
            icon=FIF.PLAY,
            text=self.translate("nav_convert"),
            onClick=self.trigger_convert,
            position=NavigationItemPosition.BOTTOM,
        )

        # qfluentwidgets defaults need a very wide window before inline expand; lower
        # the threshold so the nav shows labels at our typical window size.
        self.navigationInterface.setMinimumExpandWidth(760)

        self.stackedWidget.currentChanged.connect(self._on_main_stack_page_changed)
        self.navigationInterface.displayModeChanged.connect(
            lambda *_: self._apply_content_cap_for_current_page()
        )
        self._on_main_stack_page_changed(self.stackedWidget.currentIndex())

    def _apply_nav_menu_button_icon(self, theme_key: str) -> None:
        """Replace default Fluent MENU (hamburger) bars with a loop mark on the nav toggle."""
        self.navigationInterface.panel.menuButton.setIcon(
            make_nav_menu_toggle_icon(theme_key)
        )

    def _available_content_host_width(self) -> int:
        """Width of the area to the right of the nav (not the full window)."""
        hw = self._main_content_host.width()
        if hw > 80:
            return max(hw, 400)
        fw = self.width()
        if fw < 100:
            screen = QGuiApplication.primaryScreen()
            fw = screen.availableGeometry().width() if screen else 1600
        return max(fw - _NAV_AND_CHROME_RESERVE_PX, 400)

    def _main_column_width(self) -> int:
        """Same max for Home / Settings / Help; shrinks on narrow windows."""
        avail = self._available_content_host_width()
        return max(min(avail, _MAIN_COLUMN_MAX_WIDTH_PX), 640)

    def _pin_content_cap_width(self, w: int) -> None:
        w = max(int(w), 320)
        self._main_content_cap.setMinimumWidth(w)
        self._main_content_cap.setMaximumWidth(w)

    def _apply_content_cap_for_current_page(self) -> None:
        self._pin_content_cap_width(self._main_column_width())

    def _on_main_stack_page_changed(self, _index: int) -> None:
        self._apply_content_cap_for_current_page()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._apply_content_cap_for_current_page()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._apply_content_cap_for_current_page()
        if self._did_schedule_initial_nav_expand:
            return
        self._did_schedule_initial_nav_expand = True
        # singleShot(0) can run before Win32 has marked nav children visible; 100ms is reliable.
        QTimer.singleShot(100, self._expand_navigation_panel_initial)

    def _expand_navigation_panel_initial(self) -> None:
        self.ensure_navigation_expanded()

    def ensure_navigation_expanded(self) -> None:
        """Open the nav rail with labels; safe after show() when widgets are visible."""
        try:
            if self.navigationInterface.panel.isCollapsed():
                self.navigationInterface.expand(useAni=False)
        except Exception:
            pass

    def _on_theme_mode_changed(self, _mode: str) -> None:
        self.apply_theme()

    def trigger_convert(self) -> None:
        self.switchTo(self.homeInterface)
        self.homeInterface.convert_files()

    def apply_theme(self) -> None:
        theme_mode = self.settings_manager.get_theme_mode()
        effective = apply_app_theme(theme_mode)
        self.setStyleSheet(build_app_stylesheet(effective))
        self._apply_title_bar_chrome(theme_key=effective)
        self._apply_navigation_panel_chrome(theme_key=effective)
        self._apply_nav_menu_button_icon(effective)
        self.homeInterface.apply_theme_styles(effective)

    def _apply_title_bar_chrome(self, *, theme_key: str) -> None:
        """Re-tint the caption strip.

        qfluentwidgets registers a per-widget stylesheet on ``FluentTitleBar`` (from
        ``fluent_window.qss``) with ``background-color: transparent``. That wins over
        rules set only on ``FluentWindow``, so parent QSS never paints the title bar.
        On Windows 11, transparent + Mica also reads lighter than the solid nav/content
        chrome. Push the intended fill through the library's custom QSS channel.
        """
        self.titleBar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        if theme_key == "perfect_dark":
            dark_qss = "FluentTitleBar { background-color: #202020; }"
        else:
            dark_qss = "FluentTitleBar { background-color: transparent; }"
        light_qss = "FluentTitleBar { background-color: transparent; }"
        setCustomStyleSheet(self.titleBar, light_qss, dark_qss)

    def _apply_navigation_panel_chrome(self, *, theme_key: str) -> None:
        """NavigationPanel's bundled qss uses ``[menu=false]`` / ``[menu=true]``; a bare ``NavigationPanel``
        rule loses on specificity, so transparent kept winning and the rail never matched the title bar.
        """
        panel = self.navigationInterface.panel
        if theme_key == "perfect_dark":
            # Match library selectors; !important beats equal-specificity rules from the same sheet order.
            nav_fill = (
                "NavigationPanel[menu=false] { background-color: #202020 !important; }\n"
                "NavigationPanel[menu=true] { background-color: #202020 !important; }\n"
                "NavigationPanel[transparent=true] { background-color: #202020 !important; }"
            )
            setCustomStyleSheet(panel, "", nav_fill)
        else:
            setCustomStyleSheet(panel, "", "")

    def show_about(self) -> None:
        dlg = AboutDialog(self.translate, self)
        dlg.exec()

    def closeEvent(self, event) -> None:
        self.settings_manager.set_window_geometry(self.saveGeometry().data())
        self.homeInterface.shutdown()
        super().closeEvent(event)

    def translate(self, key: str) -> str:
        current_lang = self.settings_manager.get_current_language() or DEFAULT_LANG
        return get_translation(current_lang, key)
