import pytest

from markitdowngui.core import openai_endpoint


def test_filter_likely_vision_models_matches_common_ids():
    ids = [
        "text-only-7b",
        "llava-v1.5-7b",
        "meta-llama/Llama-3.2-11B-Vision-Instruct",
        "qwen2.5-vl-7b",
        "gpt-4o-mini",
    ]
    got = openai_endpoint.filter_likely_vision_models(ids)
    assert got == [
        "llava-v1.5-7b",
        "meta-llama/Llama-3.2-11B-Vision-Instruct",
        "qwen2.5-vl-7b",
        "gpt-4o-mini",
    ]


def test_filter_likely_vision_models_dedupes_and_preserves_order():
    ids = ["llava-a", "llava-a", "moondream2"]
    assert openai_endpoint.filter_likely_vision_models(ids) == ["llava-a", "moondream2"]


def test_test_openai_compatible_endpoint_requires_url():
    with pytest.raises(RuntimeError, match="base URL"):
        openai_endpoint.test_openai_compatible_endpoint("  ")


def test_fetch_openai_compatible_model_ids_requires_url():
    with pytest.raises(RuntimeError, match="base URL"):
        openai_endpoint.fetch_openai_compatible_model_ids("")


def test_test_openai_compatible_endpoint_uses_client(monkeypatch):
    captured = {}

    class FakeModels:
        data = [type("M", (), {"id": "a"})(), type("M", (), {"id": "b"})()]

    class FakeClient:
        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs

        class models_ns:
            @staticmethod
            def list():
                return FakeModels()

        models = models_ns()

    monkeypatch.setattr(openai_endpoint, "_require_openai", lambda: FakeClient)

    msg = openai_endpoint.test_openai_compatible_endpoint("http://localhost:1234/v1")
    assert "Connected" in msg
    assert "2 model" in msg
    assert captured["kwargs"]["base_url"] == "http://localhost:1234/v1"


def test_fetch_openai_compatible_model_ids_sorted_unique(monkeypatch):
    class FakeModels:
        data = [
            type("M", (), {"id": "z"})(),
            type("M", (), {"id": "a"})(),
            type("M", (), {"id": "a"})(),
        ]

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        class models_ns:
            @staticmethod
            def list():
                return FakeModels()

        models = models_ns()

    monkeypatch.setattr(openai_endpoint, "_require_openai", lambda: FakeClient)

    ids = openai_endpoint.fetch_openai_compatible_model_ids("http://x/v1")
    assert ids == ["a", "z"]
