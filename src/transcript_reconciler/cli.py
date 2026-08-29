from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from .audit import audit_file
from .config import ConfigError, SessionConfig, load_config
from .parsers import parse_all_sources
from .pipeline import reconcile
from .rendering import render_markdown, render_review_jsonl, write_atomic


def _source_summary(config: SessionConfig, sources: dict[str, list[Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {"config": str(config.path), "sources": {}}
    for source in config.sources:
        segments = sources[source.id]
        starts = [segment.start for segment in segments if segment.start is not None]
        ends = [
            segment.end
            for segment in segments
            if segment.end is not None
        ]
        speakers = Counter(segment.speaker or "<unmapped>" for segment in segments)
        summary["sources"][source.id] = {
            "path": str(source.path),
            "format": source.format,
            "roles": list(source.roles),
            "segments": len(segments),
            "timed_segments": len(starts),
            "start": min(starts) if starts else None,
            "end": max(ends or starts) if (ends or starts) else None,
            "speakers": dict(speakers),
        }
    return summary


def _path_argument(value: str | None, configured: Path | None, label: str) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    if configured:
        return configured
    raise ConfigError(f"{label} is required on the command line or in output config")


def command_inspect(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    sources = parse_all_sources(config)
    print(json.dumps(_source_summary(config, sources), ensure_ascii=False, indent=2))
    return 0


def command_reconcile(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    sources = parse_all_sources(config)
    result = reconcile(config, sources)
    output_path = _path_argument(args.output, config.output.path, "--output")
    review_path = _path_argument(args.review, config.output.review_path, "--review")
    write_atomic(output_path, render_markdown(result.chunks, config.output))
    write_atomic(review_path, render_review_jsonl(result.reviews))
    payload = dict(result.summary)
    payload.update({"output": str(output_path), "review": str(review_path)})
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def command_audit(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    input_path = _path_argument(args.input, config.output.path, "--input")
    if not input_path.is_file():
        raise ConfigError(f"Transcript not found: {input_path}")
    report = audit_file(input_path, config.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="transcript-reconcile",
        description="Reconcile multiple transcript sources and surface ambiguous boundaries.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser(
        "inspect", help="Parse sources and report timing, speakers, and coverage"
    )
    inspect_parser.add_argument("--config", required=True)
    inspect_parser.set_defaults(func=command_inspect)

    reconcile_parser = subparsers.add_parser(
        "reconcile", help="Write a provisional transcript and JSONL review report"
    )
    reconcile_parser.add_argument("--config", required=True)
    reconcile_parser.add_argument("--output")
    reconcile_parser.add_argument("--review")
    reconcile_parser.set_defaults(func=command_reconcile)

    audit_parser = subparsers.add_parser(
        "audit", help="Audit transcript labels, structure, duplicates, and forbidden text"
    )
    audit_parser.add_argument("--config", required=True)
    audit_parser.add_argument("--input")
    audit_parser.set_defaults(func=command_audit)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        code = args.func(args)
    except (ConfigError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        code = 2
    raise SystemExit(code)
