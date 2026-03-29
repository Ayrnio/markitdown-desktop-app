import types

from markitdowngui.core import llm_vision_chat


def test_transcribe_image_file_openai_compatible_reads_file_and_calls_api(
    tmp_path, monkeypatch
):
    png = tmp_path / "p.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n")

    captured: dict = {}

    def fake_create(*, model, messages):
        captured["model"] = model
        captured["messages"] = messages
        return types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    message=types.SimpleNamespace(content="## Hello")
                )
            ]
        )

    client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=fake_create)
        )
    )

    out = llm_vision_chat.transcribe_image_file_openai_compatible(
        client,
        "m",
        image_path=str(png),
        system_prompt="SYS",
        user_message="USR",
    )

    assert out == "## Hello"
    assert captured["model"] == "m"
    assert captured["messages"][0] == {"role": "system", "content": "SYS"}
    user = captured["messages"][1]
    assert user["role"] == "user"
    parts = user["content"]
    assert parts[0] == {"type": "text", "text": "USR"}
    assert parts[1]["type"] == "image_url"
    assert parts[1]["image_url"]["url"].startswith("data:image/png;base64,")
