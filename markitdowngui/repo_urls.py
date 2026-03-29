"""Canonical GitHub owner/repo for this fork (update checks, Help, About).

This value is **authoritative** for in-app URLs. Do not rely on ``importlib.metadata``
here: stale or upstream wheel metadata can still list the original fork and would
send users to the wrong repository.

Keep ``pyproject.toml`` ``[project.urls]`` aligned for packaging and GitHub’s UI.
"""

from __future__ import annotations

# Must match the public fork (same as [project.urls] Repository path).
GITHUB_REPO_SLUG = "Ayrnio/MarkdownAlchemy"


def github_repo_slug() -> str:
    return GITHUB_REPO_SLUG


def github_repo_home_url() -> str:
    return f"https://github.com/{github_repo_slug()}"


def github_releases_page_url() -> str:
    return f"{github_repo_home_url()}/releases"


def github_releases_latest_api_url() -> str:
    return f"https://api.github.com/repos/{github_repo_slug()}/releases/latest"
