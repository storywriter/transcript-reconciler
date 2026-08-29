#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


SKILL_NAME = "merge-transcripts"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SKILL_SOURCE = REPOSITORY_ROOT / ".agents" / "skills" / SKILL_NAME


def install(target_root: Path) -> Path:
    source = SKILL_SOURCE.resolve()
    if not (source / "SKILL.md").is_file():
        raise RuntimeError(f"Skill source is incomplete: {source}")
    target_root = target_root.expanduser().resolve()
    target_root.mkdir(parents=True, exist_ok=True)
    target = target_root / SKILL_NAME
    if target.is_symlink():
        if target.resolve() == source:
            return target
        raise RuntimeError(f"Refusing to replace existing symlink: {target}")
    if target.exists():
        raise RuntimeError(f"Refusing to replace existing path: {target}")
    target.symlink_to(source, target_is_directory=True)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Install the repository's Codex Skill")
    parser.add_argument(
        "--target-root",
        type=Path,
        default=Path.home() / ".agents" / "skills",
        help="Skill parent directory (default: ~/.agents/skills)",
    )
    args = parser.parse_args()
    try:
        target = install(args.target_root)
    except RuntimeError as exc:
        parser.error(str(exc))
    print(f"Installed {SKILL_NAME}: {target} -> {SKILL_SOURCE.resolve()}")


if __name__ == "__main__":
    main()
