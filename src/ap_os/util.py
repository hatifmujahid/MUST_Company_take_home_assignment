from __future__ import annotations

import anthropic


def extract_json_text(response: "anthropic.types.Message") -> str:
    """Structured-output responses can include a ThinkingBlock before the TextBlock."""
    for block in response.content:
        if block.type == "text":
            return block.text
    raise ValueError("No text block found in Claude response")
