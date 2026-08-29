from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

from .config import OutputConfig
from .text import normalize


def audit_text(text: str, output: OutputConfig) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    paragraphs = [part for part in re.split(r"\n{2,}", text.strip()) if part.strip()]
    label_re = re.compile(output.label_regex, re.S)
    speaker_counts: Counter[str] = Counter()
    normalized_texts: list[str] = []

    if "\n\n\n" in text:
        errors.append(
            {
                "code": "excess_blank_lines",
                "message": "Found three or more consecutive newlines",
            }
        )
    if output.prohibit_headings:
        for line_number, line in enumerate(text.splitlines(), start=1):
            if re.match(r"^#{1,6}\s", line):
                errors.append(
                    {
                        "code": "heading_present",
                        "line": line_number,
                        "message": line,
                    }
                )

    for index, paragraph in enumerate(paragraphs):
        match = label_re.fullmatch(paragraph.strip())
        if not match:
            errors.append(
                {
                    "code": "invalid_paragraph_label",
                    "paragraph": index,
                    "message": paragraph[:160],
                }
            )
            normalized_texts.append(normalize(paragraph))
            continue
        groups = match.groupdict()
        speaker = groups.get("speaker", "").strip()
        body = groups.get("text", "").strip()
        speaker_counts[speaker] += 1
        normalized_texts.append(normalize(body))
        if output.allowed_speakers and speaker not in output.allowed_speakers:
            errors.append(
                {
                    "code": "disallowed_speaker",
                    "paragraph": index,
                    "speaker": speaker,
                }
            )
        if "\n" in paragraph:
            errors.append(
                {
                    "code": "multiline_paragraph",
                    "paragraph": index,
                    "message": "Every chunk must stay in one paragraph",
                }
            )

    for index in range(1, len(normalized_texts)):
        if normalized_texts[index] and normalized_texts[index] == normalized_texts[index - 1]:
            errors.append(
                {
                    "code": "adjacent_duplicate",
                    "paragraph": index,
                }
            )

    for pattern in output.forbidden_patterns:
        try:
            matches = list(re.finditer(pattern, text))
        except re.error as exc:
            errors.append(
                {
                    "code": "invalid_forbidden_pattern",
                    "pattern": pattern,
                    "message": str(exc),
                }
            )
            continue
        if matches:
            errors.append(
                {
                    "code": "forbidden_pattern",
                    "pattern": pattern,
                    "count": len(matches),
                }
            )

    for opening, closing in output.quote_pairs:
        opening_count = text.count(opening)
        closing_count = text.count(closing)
        if opening_count != closing_count:
            errors.append(
                {
                    "code": "unbalanced_quotes",
                    "opening": opening,
                    "closing": closing,
                    "opening_count": opening_count,
                    "closing_count": closing_count,
                }
            )

    if text and not text.endswith("\n"):
        warnings.append(
            {
                "code": "missing_final_newline",
                "message": "The transcript does not end with a newline",
            }
        )

    return {
        "ok": not errors,
        "paragraphs": len(paragraphs),
        "speaker_counts": dict(speaker_counts),
        "errors": errors,
        "warnings": warnings,
    }


def audit_file(path: Path, output: OutputConfig) -> dict[str, Any]:
    return audit_text(path.read_text(encoding="utf-8"), output)
