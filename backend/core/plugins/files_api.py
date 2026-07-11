"""Files API — upload documents to Anthropic and reference them by file_id."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import anthropic

from backend.core.config import settings

_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


async def upload_file(path: str, mime_type: str = "application/pdf") -> str:
    """Upload a file to the Anthropic Files API and return its file_id."""
    file_bytes = Path(path).read_bytes()
    filename = Path(path).name
    response = await _client.beta.files.upload(
        file=(filename, file_bytes, mime_type),
    )
    return response.id


async def complete_with_file(
    file_id: str,
    prompt: str,
    model: str = "claude-opus-4-5",
    max_tokens: int = 4096,
) -> str:
    """Send a prompt referencing an already-uploaded file by file_id."""
    message = await _client.beta.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {"type": "file", "file_id": file_id},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        betas=["files-api-2025-04-14"],
    )
    return message.content[0].text


async def delete_file(file_id: str) -> None:
    """Delete a previously uploaded file."""
    await _client.beta.files.delete(file_id)


async def list_files() -> list[dict[str, Any]]:
    """List all uploaded files for this API key."""
    page = await _client.beta.files.list()
    return [{"id": f.id, "filename": f.filename, "size": f.size} for f in page.data]
