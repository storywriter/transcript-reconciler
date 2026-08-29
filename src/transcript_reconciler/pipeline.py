from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from .config import ConfigError, SessionConfig
from .models import Chunk, ReconcileResult, Segment
from .text import clean_text, shared_match_size


def overlap_seconds(segment: Segment, start: float, end: float) -> float:
    if segment.start is None:
        return 0.0
    segment_end = segment.end if segment.end is not None else segment.start + 0.001
    return max(0.0, min(segment_end, end) - max(segment.start, start))


def segments_for_interval(
    segments: Iterable[Segment], start: float, end: float
) -> list[Segment]:
    return [segment for segment in segments if overlap_seconds(segment, start, end) > 0]


def _fallback_speaker(segment: Segment, config: SessionConfig) -> str:
    fallback = config.fallback
    value = str(segment.metadata.get(fallback.metadata_field, "")).casefold()
    if fallback.metadata_field and value:
        if value in fallback.true_values and fallback.true_speaker:
            return fallback.true_speaker
        if value not in fallback.true_values and fallback.false_speaker:
            return fallback.false_speaker
    if (
        segment.speaker
        and (
            not config.output.allowed_speakers
            or segment.speaker in config.output.allowed_speakers
        )
    ):
        return segment.speaker
    return fallback.default_speaker or fallback.false_speaker or fallback.true_speaker


def _evidence(
    skeleton: Segment,
    boundary: list[Segment],
    start: float,
    end: float,
    minimum: int,
) -> tuple[Counter[str], list[dict[str, Any]]]:
    scores: Counter[str] = Counter()
    cue_records: list[dict[str, Any]] = []
    for cue in boundary:
        shared = shared_match_size(skeleton.text, cue.text, minimum)
        overlap = overlap_seconds(cue, start, end)
        if cue.speaker:
            if shared:
                scores[cue.speaker] += shared * 10
            scores[cue.speaker] += round(overlap * 2)
        cue_records.append(
            {
                "index": cue.index,
                "start": cue.start,
                "end": cue.end,
                "speaker": cue.speaker,
                "raw_speaker": cue.raw_speaker,
                "text": cue.text,
                "shared_chars": shared,
                "overlap_seconds": round(overlap, 3),
            }
        )
    return scores, cue_records


def _additional_evidence(
    skeleton: Segment,
    start: float,
    end: float,
    source_id: str,
    segments: list[Segment],
    config: SessionConfig,
) -> list[dict[str, Any]]:
    timed = [segment for segment in segments if segment.start is not None]
    if timed:
        matches = segments_for_interval(timed, start, end)
        ranked = [
            (
                shared_match_size(
                    skeleton.text, match.text, config.alignment.min_anchor_chars
                ),
                overlap_seconds(match, start, end),
                match,
            )
            for match in matches
        ]
    else:
        ranked = [
            (
                shared_match_size(
                    skeleton.text, match.text, config.alignment.min_anchor_chars
                ),
                0.0,
                match,
            )
            for match in segments
        ]
    ranked = [item for item in ranked if item[0] > 0 or item[1] > 0]
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    records: list[dict[str, Any]] = []
    for shared, overlap, match in ranked[: config.alignment.evidence_max_matches]:
        records.append(
            {
                "source": source_id,
                "index": match.index,
                "start": match.start,
                "end": match.end,
                "speaker": match.speaker,
                "raw_speaker": match.raw_speaker,
                "text": match.text,
                "shared_chars": shared,
                "overlap_seconds": round(overlap, 3),
            }
        )
    return records


def _validate_chunk_speaker(speaker: str, config: SessionConfig, segment: int) -> None:
    if not speaker:
        raise ConfigError(f"Could not infer a speaker for skeleton segment {segment}")
    if config.output.allowed_speakers and speaker not in config.output.allowed_speakers:
        raise ConfigError(
            f"Speaker {speaker!r} in skeleton segment {segment} is not allowed"
        )


def reconcile(
    config: SessionConfig, sources: dict[str, list[Segment]]
) -> ReconcileResult:
    skeleton = sources[config.alignment.skeleton_source]
    boundary = sources[config.alignment.boundary_source]
    if not skeleton:
        raise ConfigError("Skeleton source is empty")
    if not boundary:
        raise ConfigError("Boundary source is empty")
    if any(segment.start is None for segment in skeleton):
        raise ConfigError(
            "Every skeleton segment needs a timestamp in this version; configure its start column"
        )
    if any(segment.start is None for segment in boundary):
        raise ConfigError("Every boundary segment needs a timestamp")

    skeleton_indexes = {segment.index for segment in skeleton}
    missing_override_segments = sorted(set(config.overrides) - skeleton_indexes)
    if missing_override_segments:
        raise ConfigError(
            "Overrides reference missing skeleton segments: "
            + ", ".join(map(str, missing_override_segments))
        )

    boundary_end = max(
        (segment.end if segment.end is not None else segment.start or 0.0)
        for segment in boundary
    )
    chunks: list[Chunk] = []
    reviews: list[dict[str, Any]] = []
    unresolved_candidates = 0
    overridden_segments = 0
    boundary_overridden_segments = 0
    override_kinds: Counter[str] = Counter()

    for position, row in enumerate(skeleton):
        assert row.start is not None
        flags: list[str] = []
        if position + 1 < len(skeleton):
            next_start = skeleton[position + 1].start
            assert next_start is not None
            if next_start <= row.start:
                flags.append("non_increasing_skeleton_time")
                interval_end = (
                    row.end if row.end is not None and row.end > row.start else row.start + 0.001
                )
            else:
                interval_end = next_start
        else:
            interval_end = max(
                boundary_end + 0.001,
                row.end if row.end is not None else row.start + 0.001,
            )

        interval_cues = segments_for_interval(boundary, row.start, interval_end)
        scores, cue_records = _evidence(
            row,
            interval_cues,
            row.start,
            interval_end,
            config.alignment.min_anchor_chars,
        )
        fallback = _fallback_speaker(row, config)
        inferred = scores.most_common(1)[0][0] if scores else fallback
        score_items = scores.most_common()
        distinct_speakers = list(
            dict.fromkeys(cue.speaker for cue in interval_cues if cue.speaker)
        )
        meaningful = [
            speaker
            for speaker, score in score_items
            if score >= config.alignment.meaningful_speaker_score
        ]

        if not interval_cues:
            flags.append("no_boundary_evidence")
        if len(distinct_speakers) > 1:
            flags.append("multiple_boundary_speakers")
        if interval_cues and max((cue["shared_chars"] for cue in cue_records), default=0) == 0:
            flags.append("no_shared_text_anchor")
        if len(score_items) > 1 and score_items[0][1] - score_items[1][1] < config.alignment.low_margin_score:
            flags.append("low_speaker_score_margin")
        if meaningful and len(meaningful) > 1:
            flags.append("multiple_meaningful_speakers")
        if inferred and fallback and inferred != fallback:
            flags.append("boundary_disagrees_with_fallback")
        if any(not cue.speaker for cue in interval_cues):
            flags.append("unmapped_boundary_speaker")

        override = config.overrides.get(row.index)
        if override is not None:
            overridden_segments += 1
            override_kinds[override.kind] += 1
            if override.resolves_boundary:
                boundary_overridden_segments += 1
            if override.chunks is not None:
                raw_chunks = override.chunks
            else:
                raw_chunks = (
                    (
                        override.speaker if override.speaker is not None else inferred,
                        override.text if override.text is not None else row.text,
                    ),
                )
        else:
            raw_chunks = ((inferred, row.text),)
        suggested: list[dict[str, str]] = []
        for speaker, text in raw_chunks:
            _validate_chunk_speaker(speaker, config, row.index)
            cleaned = clean_text(text, config.replacements)
            if not cleaned:
                continue
            chunks.append(
                Chunk(speaker=speaker, text=cleaned, source_segment=row.index)
            )
            suggested.append({"speaker": speaker, "text": cleaned})

        additional: dict[str, list[dict[str, Any]]] = {}
        for source_id, segments in sources.items():
            if source_id in {
                config.alignment.skeleton_source,
                config.alignment.boundary_source,
            }:
                continue
            additional[source_id] = _additional_evidence(
                row, row.start, interval_end, source_id, segments, config
            )

        review_trigger_flags = {
            "non_increasing_skeleton_time",
            "no_boundary_evidence",
            "multiple_meaningful_speakers",
            "boundary_disagrees_with_fallback",
            "unmapped_boundary_speaker",
        }
        needs_review = (
            any(flag in review_trigger_flags for flag in flags)
            and not (override is not None and override.resolves_boundary)
        )
        if needs_review:
            unresolved_candidates += 1
        if override is not None and override.resolves_boundary:
            confidence = "manual"
        elif needs_review:
            confidence = "low"
        elif any(
            flag in {"no_shared_text_anchor", "low_speaker_score_margin"}
            for flag in flags
        ):
            confidence = "medium"
        else:
            confidence = "high"

        reviews.append(
            {
                "segment": row.index,
                "start": row.start,
                "end": interval_end,
                "display_time": row.display_time,
                "source_speaker": row.speaker,
                "raw_source_speaker": row.raw_speaker,
                "fallback_speaker": fallback,
                "inferred_speaker": inferred,
                "text": row.text,
                "speaker_scores": dict(scores),
                "boundary_speakers": distinct_speakers,
                "boundary_cues": cue_records,
                "additional_evidence": additional,
                "suggested_chunks": suggested,
                "flags": flags,
                "confidence": confidence,
                "override_applied": override is not None,
                "override_kind": override.kind if override is not None else None,
                "boundary_override_applied": (
                    override is not None and override.resolves_boundary
                ),
                "needs_review": needs_review,
            }
        )

    summary = {
        "skeleton_source": config.alignment.skeleton_source,
        "boundary_source": config.alignment.boundary_source,
        "skeleton_segments": len(skeleton),
        "boundary_segments": len(boundary),
        "output_chunks": len(chunks),
        "unresolved_candidates": unresolved_candidates,
        "overridden_segments": overridden_segments,
        "boundary_overridden_segments": boundary_overridden_segments,
        "override_kinds": dict(override_kinds),
        "source_counts": {source_id: len(items) for source_id, items in sources.items()},
    }
    return ReconcileResult(tuple(chunks), tuple(reviews), summary)
