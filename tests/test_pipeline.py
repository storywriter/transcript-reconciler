from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path

from transcript_reconciler.audit import audit_text
from transcript_reconciler.config import ConfigError, SegmentOverride, load_config
from transcript_reconciler.parsers import parse_all_sources
from transcript_reconciler.pipeline import reconcile
from transcript_reconciler.rendering import render_markdown


FIXTURES = Path(__file__).parent / "fixtures"


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config(FIXTURES / "session.json")
        self.sources = parse_all_sources(self.config)

    def test_overrides_produce_expected_transcript(self) -> None:
        result = reconcile(self.config, self.sources)
        rendered = render_markdown(result.chunks, self.config.output)
        expected = (FIXTURES / "expected.md").read_text(encoding="utf-8")
        self.assertEqual(rendered, expected)
        self.assertEqual(result.summary["unresolved_candidates"], 0)
        self.assertEqual(result.summary["overridden_segments"], 2)
        self.assertTrue(audit_text(rendered, self.config.output)["ok"])

    def test_mixed_rows_are_candidates_without_overrides(self) -> None:
        config = replace(self.config, overrides={})
        result = reconcile(config, self.sources)
        candidates = [review for review in result.reviews if review["needs_review"]]
        self.assertEqual({review["segment"] for review in candidates}, {0, 2})
        self.assertTrue(
            all("multiple_boundary_speakers" in review["flags"] for review in candidates)
        )
        middle = result.reviews[1]
        self.assertIn("multiple_boundary_speakers", middle["flags"])
        self.assertFalse(middle["needs_review"])
        self.assertIn("notes", result.reviews[1]["additional_evidence"])

    def test_text_only_override_does_not_resolve_speaker_review(self) -> None:
        config = replace(
            self.config,
            overrides={0: SegmentOverride(text="本文だけを修正しました。")},
        )
        result = reconcile(config, self.sources)

        first = result.reviews[0]
        self.assertTrue(first["needs_review"])
        self.assertEqual(first["override_kind"], "text")
        self.assertTrue(first["override_applied"])
        self.assertFalse(first["boundary_override_applied"])
        self.assertEqual(result.chunks[0].text, "本文だけを修正しました。")
        self.assertEqual(result.summary["unresolved_candidates"], 2)
        self.assertEqual(result.summary["boundary_overridden_segments"], 0)

    def test_speaker_only_override_preserves_skeleton_text(self) -> None:
        config = replace(
            self.config,
            overrides={1: SegmentOverride(speaker="ユーザー")},
        )
        result = reconcile(config, self.sources)

        middle = result.reviews[1]
        self.assertFalse(middle["needs_review"])
        self.assertEqual(middle["confidence"], "manual")
        self.assertEqual(middle["override_kind"], "speaker")
        self.assertEqual(result.chunks[1].speaker, "ユーザー")
        self.assertEqual(result.chunks[1].text, self.sources["readable"][1].text)

    def test_missing_override_segment_is_rejected(self) -> None:
        config = replace(
            self.config,
            overrides={999: SegmentOverride(text="存在しない行です。")},
        )
        with self.assertRaisesRegex(
            ConfigError, "Overrides reference missing skeleton segments: 999"
        ):
            reconcile(config, self.sources)


if __name__ == "__main__":
    unittest.main()
