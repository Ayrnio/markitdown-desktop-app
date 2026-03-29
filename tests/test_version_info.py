from markitdowngui.version_info import get_app_version


def test_get_app_version_non_empty():
    v = get_app_version()
    assert isinstance(v, str)
    assert len(v) > 0
