from __future__ import annotations

import unittest
from pathlib import Path

from transcript_reconciler.config import load_config
from transcript_reconciler.parsers import parse_all_sources, parse_timestamp


FIXTURES = Path(__file__).parent / "fixtures"


class ParserTests(unittest.TestCase):
    def test_parse_timestamp_variants(self) -> None:
        self.assertEqual(parse_timestamp("6.5"), 6.5)
        self.assertEqual(parse_timestamp("01:02.500"), 62.5)
        self.assertEqual(parse_timestamp("01:02:03,250"), 3723.25)

    def test_parse_all_supported_fixture_types(self) -> None:
        config = load_config(FIXTURES / "session.json")
        sources = parse_all_sources(config)
        self.assertEqual(len(sources["readable"]), 3)
        self.assertEqual(len(sources["diarization"]), 6)
        self.assertEqual(len(sources["notes"]), 2)
        self.assertEqual(sources["diarization"][0].speaker, "山本")
        self.assertEqual(sources["notes"][1].speaker, "ユーザー")


if __name__ == "__main__":
    unittest.main()
