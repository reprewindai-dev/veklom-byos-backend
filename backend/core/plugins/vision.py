"""Multimodal vision tool — sends base64 or URL images to Claude claude-opus-4-5."""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

import anthropic

from backend.core.config import settings

_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
VISION_MODEL = "claude-opus-4-5"


def _image_block_from_path(path: str) -> dict[str, Any]:
    data = Path(path).read_bytes()
    mime = mimetypes.guess_type(path)[0] or "image/png"
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": mime,
            "data": base64.standard_b64encode(data).decode(),
        },
    }


def _image_block_from_url(url: str) -> dict[str, Any]:
    return {"type": "image", "source": {"type": "url", "url": url}}


async def analyze_image(
    prompt: str,
    image_url: str | None = None,
    image_path: str | None = None,
    max_tokens: int = 1024,
) -> str:
    """Analyze an image with a text prompt. Provide either image_url or image_path."""
    if not image_url and not image_path:
        raise ValueError("Provide either image_url or image_path")

    image_block = (
        _image_block_from_url(image_url) if image_url else _image_block_from_path(image_path)  # type: ignore[arg-type]
    )
    message = await _client.messages.create(
        model=VISION_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": [image_block, {"type": "text", "text": prompt}]}],
    )
    return message.content[0].text
