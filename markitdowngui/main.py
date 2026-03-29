"""Main entry point for the MarkItDown GUI application."""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from markitdowngui.ui.main_window import MainWindow
from markitdowngui.utils.logger import AppLogger

def main():
    """Start the MarkItDown GUI application."""
    # Initialize logging
    AppLogger.initialize()
    
    # Set High DPI scaling policy
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Create and start application
    app = QApplication(sys.argv)
    app.setApplicationName("AYRN MarkFlow")
    window = MainWindow()
    window.show()
    app.processEvents()
    window.ensure_navigation_expanded()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
