from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Raised when a session configuration is invalid."""


@dataclass(frozen=True)
class SourceConfig:
    id: str
    path: Path
    format: str
    roles: tuple[str, ...] = ()
    columns: dict[str, str] = field(default_factory=dict)
    speaker_map: dict[str, str] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AlignmentConfig:
    skeleton_source: str
    boundary_source: str
    min_anchor_chars: int = 4
    meaningful_speaker_score: int = 30
    low_margin_score: int = 15
    evidence_max_matches: int = 3


@dataclass(frozen=True)
class FallbackConfig:
    metadata_field: str = "interviewee"
    true_values: tuple[str, ...] = ("true", "1", "yes")
    true_speaker: str = ""
    false_speaker: str = ""
    default_speaker: str = ""


@dataclass(frozen=True)
class OutputConfig:
    path: Path | None = None
    review_path: Path | None = None
    allowed_speakers: tuple[str, ...] = ()
    label_template: str = "**{speaker}:** {text}"
    label_regex: str = r"^\*\*(?P<speaker>.+?):\*\*\s+(?P<text>.+)$"
    prohibit_headings: bool = True
    forbidden_patterns: tuple[str, ...] = ()
    quote_pairs: tuple[tuple[str, str], ...] = (("「", "」"), ("『", "』"))


@dataclass(frozen=True)
class SessionConfig:
    path: Path
    sources: tuple[SourceConfig, ...]
    alignment: AlignmentConfig
    speaker_map: dict[str, str]
    fallback: FallbackConfig
    output: OutputConfig
    replacements: tuple[tuple[str, str], ...]
    overrides: dict[int, tuple[tuple[str, str], ...]]

    def source(self, source_id: str) -> SourceConfig:
        for source in self.sources:
            if source.id == source_id:
                return source
        raise ConfigError(f"Unknown source id: {source_id!r}")


def _resolve_optional_path(base: Path, value: Any) -> Path | None:
    if value in (None, ""):
        return None
    path = Path(str(value)).expanduser()
    return path if path.is_absolute() else (base / path).resolve()


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{label} must be a JSON object")
    return value


def _parse_sources(raw: Any, base: Path) -> tuple[SourceConfig, ...]:
    if not isinstance(raw, list) or len(raw) < 2:
        raise ConfigError("sources must contain at least two transcript sources")
    sources: list[SourceConfig] = []
    seen: set[str] = set()
    supported = {"csv", "vtt", "srt", "md", "txt"}
    for index, item in enumerate(raw):
        data = _require_object(item, f"sources[{index}]")
        source_id = str(data.get("id", "")).strip()
        if not source_id or source_id in seen:
            raise ConfigError(f"sources[{index}].id must be non-empty and unique")
        seen.add(source_id)
        source_path = _resolve_optional_path(base, data.get("path"))
        if source_path is None:
            raise ConfigError(f"sources[{index}].path is required")
        source_format = str(data.get("format") or source_path.suffix.lstrip(".")).lower()
        if source_format == "markdown":
            source_format = "md"
        if source_format not in supported:
            raise ConfigError(
                f"sources[{index}].format must be one of {sorted(supported)}"
            )
        columns = _require_object(data.get("columns", {}), f"sources[{index}].columns")
        speaker_map = _require_object(
            data.get("speaker_map", {}), f"sources[{index}].speaker_map"
        )
        options = _require_object(data.get("options", {}), f"sources[{index}].options")
        roles = data.get("roles", [])
        if not isinstance(roles, list):
            raise ConfigError(f"sources[{index}].roles must be an array")
        sources.append(
            SourceConfig(
                id=source_id,
                path=source_path,
                format=source_format,
                roles=tuple(str(role) for role in roles),
                columns={str(key): str(value) for key, value in columns.items()},
                speaker_map={str(key): str(value) for key, value in speaker_map.items()},
                options=options,
            )
        )
    return tuple(sources)


def _parse_quote_pairs(raw: Any) -> tuple[tuple[str, str], ...]:
    if raw is None:
        return (("「", "」"), ("『", "』"))
    if not isinstance(raw, list):
        raise ConfigError("output.quote_pairs must be an array")
    pairs: list[tuple[str, str]] = []
    for index, pair in enumerate(raw):
        if not isinstance(pair, list) or len(pair) != 2:
            raise ConfigError(f"output.quote_pairs[{index}] must contain two strings")
        pairs.append((str(pair[0]), str(pair[1])))
    return tuple(pairs)


def load_config(path: str | Path) -> SessionConfig:
    config_path = Path(path).expanduser().resolve()
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Config file not found: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {config_path}: {exc}") from exc
    data = _require_object(raw, "config")
    base = config_path.parent
    sources = _parse_sources(data.get("sources"), base)
    source_ids = {source.id for source in sources}

    alignment_raw = _require_object(data.get("alignment", {}), "alignment")
    skeleton_source = str(alignment_raw.get("skeleton_source", "")).strip()
    boundary_source = str(alignment_raw.get("boundary_source", "")).strip()
    if skeleton_source not in source_ids or boundary_source not in source_ids:
        raise ConfigError(
            "alignment.skeleton_source and boundary_source must name configured sources"
        )
    if skeleton_source == boundary_source:
        raise ConfigError("skeleton_source and boundary_source must be different")
    alignment = AlignmentConfig(
        skeleton_source=skeleton_source,
        boundary_source=boundary_source,
        min_anchor_chars=max(1, int(alignment_raw.get("min_anchor_chars", 4))),
        meaningful_speaker_score=max(
            1, int(alignment_raw.get("meaningful_speaker_score", 30))
        ),
        low_margin_score=max(0, int(alignment_raw.get("low_margin_score", 15))),
        evidence_max_matches=max(
            1, int(alignment_raw.get("evidence_max_matches", 3))
        ),
    )

    fallback_raw = _require_object(data.get("fallback", {}), "fallback")
    true_values = fallback_raw.get("true_values", ["TRUE", "1", "yes"])
    if not isinstance(true_values, list):
        raise ConfigError("fallback.true_values must be an array")
    fallback = FallbackConfig(
        metadata_field=str(fallback_raw.get("metadata_field", "interviewee")),
        true_values=tuple(str(value).casefold() for value in true_values),
        true_speaker=str(fallback_raw.get("true_speaker", "")),
        false_speaker=str(fallback_raw.get("false_speaker", "")),
        default_speaker=str(fallback_raw.get("default_speaker", "")),
    )

    output_raw = _require_object(data.get("output", {}), "output")
    allowed = output_raw.get("allowed_speakers", [])
    forbidden = output_raw.get("forbidden_patterns", [])
    if not isinstance(allowed, list) or not isinstance(forbidden, list):
        raise ConfigError(
            "output.allowed_speakers and forbidden_patterns must be arrays"
        )
    label_template = str(
        output_raw.get("label_template", "**{speaker}:** {text}")
    )
    if "{speaker}" not in label_template or "{text}" not in label_template:
        raise ConfigError("output.label_template must contain {speaker} and {text}")
    output = OutputConfig(
        path=_resolve_optional_path(base, output_raw.get("path")),
        review_path=_resolve_optional_path(base, output_raw.get("review_path")),
        allowed_speakers=tuple(str(item) for item in allowed),
        label_template=label_template,
        label_regex=str(
            output_raw.get(
                "label_regex", r"^\*\*(?P<speaker>.+?):\*\*\s+(?P<text>.+)$"
            )
        ),
        prohibit_headings=bool(output_raw.get("prohibit_headings", True)),
        forbidden_patterns=tuple(str(item) for item in forbidden),
        quote_pairs=_parse_quote_pairs(output_raw.get("quote_pairs")),
    )

    replacements_raw = data.get("replacements", [])
    if not isinstance(replacements_raw, list):
        raise ConfigError("replacements must be an array")
    replacements: list[tuple[str, str]] = []
    for index, item in enumerate(replacements_raw):
        replacement = _require_object(item, f"replacements[{index}]")
        source = str(replacement.get("from", ""))
        target = str(replacement.get("to", ""))
        if not source:
            raise ConfigError(f"replacements[{index}].from must be non-empty")
        replacements.append((source, target))

    overrides_raw = data.get("overrides", [])
    if not isinstance(overrides_raw, list):
        raise ConfigError("overrides must be an array")
    overrides: dict[int, tuple[tuple[str, str], ...]] = {}
    for index, item in enumerate(overrides_raw):
        override = _require_object(item, f"overrides[{index}]")
        segment = int(override.get("segment", -1))
        if segment < 0 or segment in overrides:
            raise ConfigError(
                f"overrides[{index}].segment must be unique and non-negative"
            )
        chunks_raw = override.get("chunks", [])
        if not isinstance(chunks_raw, list):
            raise ConfigError(f"overrides[{index}].chunks must be an array")
        chunks: list[tuple[str, str]] = []
        for chunk_index, chunk_item in enumerate(chunks_raw):
            chunk = _require_object(
                chunk_item, f"overrides[{index}].chunks[{chunk_index}]"
            )
            speaker = str(chunk.get("speaker", "")).strip()
            text = str(chunk.get("text", "")).strip()
            if not speaker or not text:
                raise ConfigError(
                    f"overrides[{index}].chunks[{chunk_index}] needs speaker and text"
                )
            chunks.append((speaker, text))
        overrides[segment] = tuple(chunks)

    speaker_map_raw = _require_object(data.get("speaker_map", {}), "speaker_map")
    speaker_map = {str(key): str(value) for key, value in speaker_map_raw.items()}
    configured_speakers = set(speaker_map.values()) | {
        fallback.true_speaker,
        fallback.false_speaker,
        fallback.default_speaker,
    }
    configured_speakers.discard("")
    if output.allowed_speakers and not configured_speakers.issubset(
        set(output.allowed_speakers)
    ):
        unknown = sorted(configured_speakers - set(output.allowed_speakers))
        raise ConfigError(f"Configured speakers missing from allowed_speakers: {unknown}")

    return SessionConfig(
        path=config_path,
        sources=sources,
        alignment=alignment,
        speaker_map=speaker_map,
        fallback=fallback,
        output=output,
        replacements=tuple(replacements),
        overrides=overrides,
    )
