from __future__ import annotations

import base64
import mimetypes
from collections.abc import Callable
from pathlib import Path


def transcribe_image_file_openai_compatible(
    client: object,
    model: str,
    *,
    image_path: str,
    system_prompt: str,
    user_message: str,
    should_cancel: Callable[[], bool] | None = None,
) -> str:
    """Call chat.completions with system + vision user content (OpenAI-compatible servers)."""
    path = Path(image_path)
    raw = path.read_bytes()
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    data_uri = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"

    messages: list[dict[str, object]] = [
        {"role": "system", "content": system_prompt.strip()},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_message.strip()},
                {
                    "type": "image_url",
                    "image_url": {"url": data_uri},
                },
            ],
        },
    ]

    if should_cancel is not None and should_cancel():
        return ""

    try:
        response = client.chat.completions.create(model=model, messages=messages)
    except Exception:
        if should_cancel is not None and should_cancel():
            return ""
        raise

    choice = response.choices[0].message
    text = getattr(choice, "content", None) or ""
    return str(text).strip()
