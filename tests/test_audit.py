from __future__ import annotations

import unittest
from pathlib import Path

from transcript_reconciler.audit import audit_text
from transcript_reconciler.config import load_config


FIXTURES = Path(__file__).parent / "fixtures"


class AuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.output = load_config(FIXTURES / "session.json").output

    def test_detects_contract_violations(self) -> None:
        text = (
            "# Metadata\n\n"
            "**Unknown:** SPEAKER_01 says 「unfinished\n\n"
            "**Unknown:** SPEAKER_01 says 「unfinished\n"
        )
        report = audit_text(text, self.output)
        codes = {error["code"] for error in report["errors"]}
        self.assertFalse(report["ok"])
        self.assertIn("heading_present", codes)
        self.assertIn("disallowed_speaker", codes)
        self.assertIn("forbidden_pattern", codes)
        self.assertIn("adjacent_duplicate", codes)
        self.assertIn("unbalanced_quotes", codes)

    def test_allows_same_text_from_adjacent_different_speakers(self) -> None:
        text = (
            "**山本:** ありがとうございます。\n\n"
            "**ユーザー:** ありがとうございます。\n"
        )
        report = audit_text(text, self.output)
        codes = {error["code"] for error in report["errors"]}

        self.assertTrue(report["ok"])
        self.assertNotIn("adjacent_duplicate", codes)


if __name__ == "__main__":
    unittest.main()
