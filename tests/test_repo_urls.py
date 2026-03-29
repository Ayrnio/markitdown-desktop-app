import pytest

from markitdowngui import repo_urls


def test_github_urls_from_slug(monkeypatch):
    monkeypatch.setattr(repo_urls, "GITHUB_REPO_SLUG", "acme/demo")
    assert repo_urls.github_repo_slug() == "acme/demo"
    assert repo_urls.github_repo_home_url() == "https://github.com/acme/demo"
    assert repo_urls.github_releases_page_url() == "https://github.com/acme/demo/releases"
    assert (
        repo_urls.github_releases_latest_api_url()
        == "https://api.github.com/repos/acme/demo/releases/latest"
    )


def test_default_slug_is_ayrnio_markdown_alchemy():
    assert repo_urls.GITHUB_REPO_SLUG == "Ayrnio/MarkdownAlchemy"
    assert repo_urls.github_repo_home_url() == "https://github.com/Ayrnio/MarkdownAlchemy"
