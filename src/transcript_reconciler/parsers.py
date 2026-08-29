from __future__ import annotations

import csv
import html
import re
from pathlib import Path
from typing import Iterable

from .config import ConfigError, SessionConfig, SourceConfig
from .models import Segment


TIMING_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})\s+-->\s+"
    r"(?P<end>\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})"
)
VOICE_RE = re.compile(r"<v(?:\.[^\s>]+)?\s+([^>]+)>(.*?)(?=</v>|$)", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
SPEAKER_RE = re.compile(
    r"^\s*(?:\*\*)?(?P<speaker>[^:\n：]{1,100})(?::|：)(?:\*\*)?\s*"
    r"(?P<text>.+)$",
    re.S,
)
LEADING_TIME_RE = re.compile(
    r"^\s*\[?(?P<start>\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d{1,3})?)\]?\s*"
)


COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "start": (
        "発話時刻(秒)",
        "開始時刻(秒)",
        "start_seconds",
        "start",
        "開始",
        "発話時刻",
        "timestamp",
        "time",
    ),
    "end": ("終了時刻(秒)", "end_seconds", "end", "終了"),
    "display_time": ("発話時刻", "表示時刻", "display_time", "timestamp", "time"),
    "speaker": ("話者名", "話者", "speaker", "name"),
    "text": ("書き起こし", "発話", "本文", "text", "transcript", "content"),
    "interviewee": ("インタビュイー？", "interviewee", "is_interviewee"),
}


def parse_timestamp(value: str | float | int | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text.replace(",", "."))
    except ValueError:
        pass
    parts = text.replace(",", ".").split(":")
    if len(parts) not in {2, 3}:
        raise ValueError(f"Invalid timestamp: {value!r}")
    try:
        numbers = [float(part) for part in parts]
    except ValueError as exc:
        raise ValueError(f"Invalid timestamp: {value!r}") from exc
    if len(numbers) == 2:
        minutes, seconds = numbers
        return minutes * 60 + seconds
    hours, minutes, seconds = numbers
    return hours * 3600 + minutes * 60 + seconds


def _map_speaker(raw: str, source: SourceConfig, config: SessionConfig) -> str:
    raw = html.unescape(raw).strip()
    locally_mapped = source.speaker_map.get(raw, raw)
    return config.speaker_map.get(locally_mapped, locally_mapped)


def _resolve_column(
    fieldnames: Iterable[str], source: SourceConfig, logical: str, required: bool = False
) -> str | None:
    available = {name.strip(): name for name in fieldnames if name is not None}
    configured = source.columns.get(logical)
    if configured:
        if configured not in available:
            raise ConfigError(
                f"Source {source.id!r} column {configured!r} for {logical!r} was not found"
            )
        return available[configured]
    for alias in COLUMN_ALIASES.get(logical, ()):
        if alias in available:
            return available[alias]
    if required:
        raise ConfigError(
            f"Source {source.id!r} needs a {logical!r} column; configure sources[].columns"
        )
    return None


def parse_csv(source: SourceConfig, config: SessionConfig) -> list[Segment]:
    with source.path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        text_column = _resolve_column(fieldnames, source, "text", required=True)
        start_column = _resolve_column(fieldnames, source, "start")
        end_column = _resolve_column(fieldnames, source, "end")
        display_column = _resolve_column(fieldnames, source, "display_time")
        speaker_column = _resolve_column(fieldnames, source, "speaker")
        interviewee_column = _resolve_column(fieldnames, source, "interviewee")
        rows = list(reader)

    segments: list[Segment] = []
    for index, row in enumerate(rows):
        text = str(row.get(text_column or "", "")).strip()
        if not text:
            continue
        raw_speaker = str(row.get(speaker_column or "", "")).strip()
        metadata = {str(key): value for key, value in row.items() if key is not None}
        if interviewee_column:
            metadata["interviewee"] = row.get(interviewee_column, "")
        try:
            start = parse_timestamp(row.get(start_column or "")) if start_column else None
            end = parse_timestamp(row.get(end_column or "")) if end_column else None
        except ValueError as exc:
            raise ConfigError(f"Source {source.id!r} row {index}: {exc}") from exc
        segments.append(
            Segment(
                source_id=source.id,
                index=index,
                start=start,
                end=end,
                display_time=str(row.get(display_column or "", "")).strip(),
                raw_speaker=raw_speaker,
                speaker=_map_speaker(raw_speaker, source, config),
                text=text,
                metadata=metadata,
            )
        )
    return segments


def _clean_markup(text: str) -> str:
    text = TAG_RE.sub("", html.unescape(text))
    return re.sub(r"\s+", " ", text).strip()


def _speaker_and_text(body: str, default_speaker: str = "") -> tuple[str, str]:
    cleaned = _clean_markup(body)
    match = SPEAKER_RE.match(cleaned)
    if match:
        return match.group("speaker").strip(), match.group("text").strip()
    return default_speaker, cleaned


def parse_caption_file(source: SourceConfig, config: SessionConfig) -> list[Segment]:
    content = source.path.read_text(encoding="utf-8-sig")
    blocks = re.split(r"\r?\n\s*\r?\n", content.strip())
    segments: list[Segment] = []
    default_speaker = str(source.options.get("default_speaker", ""))
    for block in blocks:
        timing = TIMING_RE.search(block)
        if not timing:
            continue
        try:
            start = parse_timestamp(timing.group("start"))
            end = parse_timestamp(timing.group("end"))
        except ValueError as exc:
            raise ConfigError(f"Source {source.id!r}: {exc}") from exc
        body = block[timing.end() :].strip()
        voice_matches = list(VOICE_RE.finditer(body))
        if voice_matches:
            items = [
                (match.group(1).strip(), _clean_markup(match.group(2)))
                for match in voice_matches
            ]
        else:
            items = [_speaker_and_text(body, default_speaker)]
        for raw_speaker, text in items:
            if not text:
                continue
            segments.append(
                Segment(
                    source_id=source.id,
                    index=len(segments),
                    start=start,
                    end=end,
                    display_time=timing.group("start"),
                    raw_speaker=raw_speaker,
                    speaker=_map_speaker(raw_speaker, source, config),
                    text=text,
                )
            )
    segments.sort(
        key=lambda segment: (
            float("inf") if segment.start is None else segment.start,
            float("inf") if segment.end is None else segment.end,
            segment.index,
        )
    )
    return segments


def parse_text_file(source: SourceConfig, config: SessionConfig) -> list[Segment]:
    content = source.path.read_text(encoding="utf-8-sig").strip()
    blocks = re.split(r"\r?\n\s*\r?\n", content) if content else []
    segments: list[Segment] = []
    default_speaker = str(source.options.get("default_speaker", ""))
    for block in blocks:
        compact = re.sub(r"\s*\r?\n\s*", " ", block).strip()
        if not compact or (source.format == "md" and compact.startswith("#")):
            continue
        start: float | None = None
        leading = LEADING_TIME_RE.match(compact)
        if leading:
            try:
                start = parse_timestamp(leading.group("start"))
                compact = compact[leading.end() :].strip(" -–—")
            except ValueError:
                start = None
        raw_speaker, text = _speaker_and_text(compact, default_speaker)
        if not text:
            continue
        segments.append(
            Segment(
                source_id=source.id,
                index=len(segments),
                start=start,
                display_time=leading.group("start") if leading and start is not None else "",
                raw_speaker=raw_speaker,
                speaker=_map_speaker(raw_speaker, source, config),
                text=text,
            )
        )
    return segments


def parse_source(source: SourceConfig, config: SessionConfig) -> list[Segment]:
    if not source.path.is_file():
        raise ConfigError(f"Transcript source not found: {source.path}")
    if source.format == "csv":
        return parse_csv(source, config)
    if source.format in {"vtt", "srt"}:
        return parse_caption_file(source, config)
    if source.format in {"md", "txt"}:
        return parse_text_file(source, config)
    raise ConfigError(f"Unsupported source format: {source.format}")


def parse_all_sources(config: SessionConfig) -> dict[str, list[Segment]]:
    return {source.id: parse_source(source, config) for source in config.sources}
