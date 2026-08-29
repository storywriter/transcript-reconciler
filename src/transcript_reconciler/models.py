from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Segment:
    source_id: str
    index: int
    text: str
    speaker: str = ""
    raw_speaker: str = ""
    start: float | None = None
    end: float | None = None
    display_time: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def timed(self) -> bool:
        return self.start is not None


@dataclass(frozen=True)
class Chunk:
    speaker: str
    text: str
    source_segment: int


@dataclass(frozen=True)
class ReconcileResult:
    chunks: tuple[Chunk, ...]
    reviews: tuple[dict[str, Any], ...]
    summary: dict[str, Any]
