from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from transcript_reconciler.config import ConfigError, load_config


FIXTURES = Path(__file__).parent / "fixtures"


class ConfigTests(unittest.TestCase):
    def load_with_overrides(self, overrides: list[dict[str, object]]):
        raw = json.loads((FIXTURES / "session.json").read_text(encoding="utf-8"))
        for source in raw["sources"]:
            source["path"] = str(FIXTURES / source["path"])
        raw["overrides"] = overrides

        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "session.json"
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        return load_config(path)

    def test_loads_text_speaker_and_suppression_overrides(self) -> None:
        config = self.load_with_overrides(
            [
                {"segment": 0, "text": "修正済みの本文です。"},
                {"segment": 1, "speaker": "ユーザー"},
                {"segment": 2, "chunks": []},
            ]
        )

        self.assertEqual(config.overrides[0].kind, "text")
        self.assertFalse(config.overrides[0].resolves_boundary)
        self.assertEqual(config.overrides[1].kind, "speaker")
        self.assertTrue(config.overrides[1].resolves_boundary)
        self.assertEqual(config.overrides[2].kind, "suppress")
        self.assertEqual(config.overrides[2].chunks, ())

    def test_rejects_chunks_combined_with_scalar_override(self) -> None:
        with self.assertRaisesRegex(
            ConfigError, "cannot combine chunks with speaker or text"
        ):
            self.load_with_overrides(
                [
                    {
                        "segment": 0,
                        "speaker": "山本",
                        "chunks": [{"speaker": "山本", "text": "質問です。"}],
                    }
                ]
            )

    def test_loads_combined_speaker_and_text_override(self) -> None:
        config = self.load_with_overrides(
            [
                {
                    "segment": 0,
                    "speaker": "山本",
                    "text": "話者と本文を確認しました。",
                }
            ]
        )

        override = config.overrides[0]
        self.assertEqual(override.kind, "speaker_text")
        self.assertTrue(override.resolves_boundary)

    def test_rejects_override_without_a_change(self) -> None:
        with self.assertRaisesRegex(
            ConfigError, "needs chunks, speaker, or text"
        ):
            self.load_with_overrides([{"segment": 0}])


if __name__ == "__main__":
    unittest.main()
