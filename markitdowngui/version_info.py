"""Single place to resolve the app version for UI and packaging."""

from __future__ import annotations

from importlib import metadata


def get_app_version() -> str:
    """Installed wheel/sdist version, else ``markitdowngui.__version__``."""
    try:
        return metadata.version("markitdowngui")
    except metadata.PackageNotFoundError:
        pass
    from markitdowngui import __version__ as fallback

    return fallback or "0.0.0"
