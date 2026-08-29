from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .config import OutputConfig
from .models import Chunk


def render_markdown(chunks: Iterable[Chunk], output: OutputConfig) -> str:
    paragraphs = [
        output.label_template.format(speaker=chunk.speaker, text=chunk.text)
        for chunk in chunks
    ]
    return "\n\n".join(paragraphs) + ("\n" if paragraphs else "")


def render_review_jsonl(reviews: Iterable[dict[str, Any]]) -> str:
    lines = [json.dumps(review, ensure_ascii=False, sort_keys=True) for review in reviews]
    return "\n".join(lines) + ("\n" if lines else "")


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)
