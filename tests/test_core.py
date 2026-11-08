"""核心层测试：模型、白名单、数据库与仓库。用内存库，不需要磁盘。"""

from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shiyin.app.adapters import source_catalog  # noqa: E402
from shiyin.app.core.models import Track  # noqa: E402
from shiyin.app.data import db  # noqa: E402
from shiyin.app.data.repository import Repository  # noqa: E402
from shiyin.app.ui.widgets.slider_math import value_at as slider_value_at  # noqa: E402


class TrackTest(unittest.TestCase):
    def test_id_is_stable(self):
        a = Track(source="QQMusicClient", source_id="abc", title="晴天", artist="周杰伦")
        b = Track(source="QQMusicClient", source_id="abc", title="另一个标题", artist="别人")
        self.assertEqual(a.id, b.id, "同一源同一标识必须稳定")

    def test_local_id_depends_on_path(self):
        track = Track(source="local", source_id="x", title="t", path="C:/music/a.flac")
        self.assertTrue(track.id.startswith("local:"))
        self.assertTrue(track.is_local)

    def test_merge_key_ignores_brackets_and_duration_noise(self):
        a = Track(title="晴天 (Live)", artist="周杰伦/某某", duration_ms=180000)
        b = Track(title="晴天", artist="周杰伦", duration_ms=181000)
        self.assertEqual(a.merge_key, b.merge_key)

    def test_quality_score_prefers_lossless(self):
        lossless = Track(title="a", source="x", source_id="1", ext="flac", bitrate=900)
        lossy = Track(title="a", source="x", source_id="2", ext="mp3", bitrate=320)
        self.assertGreater(lossless.quality_score, lossy.quality_score)
        self.assertEqual(lossless.ext_clean, "flac")

    def test_to_dict_drops_raw(self):
        data = Track(title="a").to_dict()
        self.assertNotIn("raw", data)


class CatalogTest(unittest.TestCase):
    def test_whitelist_is_consistent(self):
        names = source_catalog.all_sources()
        self.assertGreaterEqual(len(names), 30)
        enabled = source_catalog.default_enabled_sources()
        self.assertTrue(all(name in names for name in enabled))
        self.assertTrue(all(name not in names for name in source_catalog.excluded_sources()))

    def test_label(self):
        self.assertEqual(source_catalog.source_label("QQMusicClient"), "QQ")


class SliderMathTest(unittest.TestCase):
    """音量/进度条点击跳转的坐标换算。"""

    def test_edges_are_reachable(self):
        self.assertEqual(slider_value_at(0, 0, 100, width=300), 0)
        self.assertEqual(slider_value_at(300, 0, 100, width=300), 100)

    def test_middle_is_half(self):
        self.assertEqual(slider_value_at(150, 0, 100, width=300), 50)

    def test_quarter_and_three_quarters(self):
        # 手柄半径会让两端各留白，允许 ±15 的偏差
        self.assertAlmostEqual(slider_value_at(75, 0, 1000, width=300), 250, delta=15)
        self.assertAlmostEqual(slider_value_at(225, 0, 1000, width=300), 750, delta=15)

    def test_clamped_outside(self):
        self.assertEqual(slider_value_at(-40, 0, 60, width=200), 0)
        self.assertEqual(slider_value_at(400, 0, 60, width=200), 60)

    def test_degenerate_ranges(self):
        self.assertEqual(slider_value_at(50, 7, 7, width=100), 7)
        # 宽度还没布局出来时不越界，按比例直接钳到最大值
        self.assertEqual(slider_value_at(50, 0, 10, width=0), 10)


class RepositoryTest(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        db.init_db(self.conn)
        self.repo = Repository(self.conn)
        self.repo.ensure_default_playlists()

    def test_upsert_and_list(self):
        track = Track(title="夜曲", artist="周杰伦", source="local", source_id="f1", path="C:/a.mp3")
        self.repo.upsert_track(track, fingerprint="f1")
        self.assertEqual(self.repo.count_tracks(), 1)
        found = self.repo.list_tracks(keyword="夜曲")
        self.assertEqual(len(found), 1)
        self.assertEqual(self.repo.find_local_by_fingerprint("f1").title, "夜曲")

    def test_playlist_roundtrip(self):
        track = Track(title="t", source="local", source_id="x1", path="C:/b.mp3")
        self.repo.upsert_track(track)
        self.repo.add_to_playlist("favorites", track)
        items = self.repo.playlist_tracks("favorites")
        self.assertEqual(len(items), 1)

    def test_favorite_without_prior_upsert_is_visible(self):
        """收藏不能依赖先入库：在线搜到、没下载的曲子也要能收藏上。"""
        track = Track(title="晴天", artist="周杰伦", source="QQMusicClient", source_id="abc")
        self.repo.add_to_playlist("favorites", track)
        self.assertEqual([t.title for t in self.repo.playlist_tracks("favorites")], ["晴天"])
        self.assertTrue(self.repo.is_in_playlist("favorites", track.id))
        self.repo.remove_from_playlist("favorites", track.id)
        self.assertFalse(self.repo.is_in_playlist("favorites", track.id))
        self.assertEqual(len(self.repo.playlist_tracks("favorites")), 0)

    def test_recent_is_newest_first_and_deduped(self):
        first = Track(title="第一首", source="X", source_id="1")
        second = Track(title="第二首", source="X", source_id="2")
        self.repo.add_to_playlist("recent", first)
        self.repo.add_to_playlist("recent", second)
        newest = [t.title for t in self.repo.playlist_tracks("recent", newest_first=True)]
        self.assertEqual(newest, ["第二首", "第一首"])
        # 再播一次第一首：顶到最前，不产生重复行
        self.repo.add_to_playlist("recent", first)
        newest = [t.title for t in self.repo.playlist_tracks("recent", newest_first=True)]
        self.assertEqual(newest, ["第一首", "第二首"])
        self.repo.clear_playlist("recent")
        self.assertEqual(len(self.repo.playlist_tracks("recent")), 0)

    def test_user_playlist_lifecycle(self):
        pid = self.repo.create_playlist("通勤")
        self.repo.add_to_playlist(pid, Track(title="t", source="X", source_id="9"))
        self.assertEqual(len(self.repo.playlist_tracks(pid)), 1)
        self.repo.rename_playlist(pid, "通勤歌单")
        names = [p["name"] for p in self.repo.list_playlists() if p["id"] == pid]
        self.assertEqual(names, ["通勤歌单"])
        self.assertTrue(self.repo.delete_playlist(pid))
        self.assertFalse(any(p["id"] == pid for p in self.repo.list_playlists()))
        # 内置列表不允许删除
        self.assertFalse(self.repo.delete_playlist("favorites"))

    def test_orphan_items_do_not_inflate_count(self):
        """playlist_items 里的孤儿记录（历史遗留）不应计入歌单数量。"""
        self.repo._conn.execute(
            "INSERT INTO playlist_items(playlist_id, track_id, position, added_at) VALUES(?,?,?,?)",
            ("favorites", "not-in-tracks", 1.0, 1),
        )
        self.repo._conn.commit()
        favorites = [p for p in self.repo.list_playlists() if p["id"] == "favorites"][0]
        self.assertEqual(favorites["count"], 0)

    def test_favorite_keeps_downloaded_path(self):
        """把已下载的曲子从搜索结果再收藏一次，不能把本地路径冲掉。"""
        downloaded = Track(title="晴天", source="QQMusicClient", source_id="abc", path="C:/music/晴天.mp3")
        self.repo.upsert_track(downloaded)
        online = Track(title="晴天", source="QQMusicClient", source_id="abc")  # 搜索返回的没有 path
        self.repo.add_to_playlist("favorites", online)
        stored = self.repo.get_track(downloaded.id)
        self.assertEqual(stored.path, "C:/music/晴天.mp3")

    def test_online_favorite_does_not_enter_local_library(self):
        """在线收藏只进收藏夹，不能冒充本地库曲目。"""
        online = Track(title="晴天", artist="周杰伦", source="QQMusicClient", source_id="abc")
        self.repo.add_to_playlist("favorites", online)
        self.assertEqual(self.repo.count_tracks(), 0)
        self.assertEqual(len(self.repo.list_tracks()), 0)
        self.assertEqual(len(self.repo.playlist_tracks("favorites")), 1)

    def test_health(self):
        self.repo.record_source_ok("A")
        self.repo.record_source_fail("A")
        health = self.repo.health("A")
        self.assertEqual(health["success"], 1)
        self.assertEqual(health["failure"], 1)


if __name__ == "__main__":
    unittest.main()
