from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher


def normalize(text: str) -> str:
    chars: list[str] = []
    for char in unicodedata.normalize("NFKC", text):
        category = unicodedata.category(char)
        if char.isspace() or category.startswith(("P", "S")):
            continue
        chars.append(char.casefold())
    return "".join(chars)


def shared_match_size(left: str, right: str, minimum: int = 4) -> int:
    left_norm = normalize(left)
    right_norm = normalize(right)
    if not left_norm or not right_norm:
        return 0
    return sum(
        block.size
        for block in SequenceMatcher(
            None, left_norm, right_norm, autojunk=False
        ).get_matching_blocks()
        if block.size >= minimum
    )


def clean_text(text: str, replacements: tuple[tuple[str, str], ...]) -> str:
    result = unicodedata.normalize("NFC", text)
    for source, target in replacements:
        result = result.replace(source, target)
    result = re.sub(r"[ \t]+", " ", result)
    result = re.sub(r"\s*\n\s*", " ", result)
    result = re.sub(r"\s+([、。？！])", r"\1", result)
    return result.strip()
