"""服务层纯逻辑测试：跨源归并、文件名清洗、配置读写。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shiyin.app.core.models import SearchResult, Track  # noqa: E402
from shiyin.app.services.download_service import safe_filename  # noqa: E402
from shiyin.app.services.search_service import SearchService  # noqa: E402
from shiyin.app.services.settings_service import SettingsService  # noqa: E402


class MergeTest(unittest.TestCase):
    def test_merge_keeps_best_and_alternatives(self):
        flac = Track(title="晴天", artist="周杰伦", source="A", source_id="1", ext="flac", duration_ms=180000)
        mp3 = Track(title="晴天", artist="周杰伦", source="B", source_id="2", ext="mp3", bitrate=320,
                    duration_ms=181000)
        merged = SearchService._merge({"A": [flac], "B": [mp3]})
        self.assertEqual(len(merged), 1)
        best = merged[0]
        self.assertEqual(best.source, "A")
        self.assertEqual(len(best.alternatives), 1)
        self.assertEqual(best.alternatives[0].source, "B")

    def test_merge_same_source_duplicates_collapse(self):
        a = Track(title="x", artist="y", source="A", source_id="1")
        b = Track(title="x", artist="y", source="A", source_id="2")
        merged = SearchService._merge({"A": [a, b]})
        self.assertEqual(len(merged), 1)

    def test_search_result_summary(self):
        result = SearchResult(keyword="k", items=[Track(title="a")], per_source={"A": 1},
                             errors={"B": "超时"})
        self.assertIn("1", result.summary)


class FilenameTest(unittest.TestCase):
    def test_safe_filename(self):
        self.assertEqual(safe_filename('a/b:c*d?"e'), "a_b_c_d_e")
        self.assertEqual(safe_filename("   "), "track")
        self.assertTrue(len(safe_filename("长" * 400)) <= 120)


class SettingsTest(unittest.TestCase):
    def test_roundtrip(self):
        path = Path(tempfile.mkdtemp()) / "config.json"
        settings = SettingsService(path)
        settings.set("volume", 0.5)
        settings.update({"concurrency": 4, "enabled_sources": ["QQMusicClient"]})
        reloaded = SettingsService(path)
        self.assertEqual(reloaded.get("volume"), 0.5)
        self.assertEqual(reloaded.get("concurrency"), 4)
        self.assertEqual(reloaded.enabled_sources, ["QQMusicClient"])

    def test_empty_sources_fall_back(self):
        path = Path(tempfile.mkdtemp()) / "config.json"
        settings = SettingsService(path)
        settings.set("enabled_sources", [])
        self.assertTrue(settings.enabled_sources)


if __name__ == "__main__":
    unittest.main()
