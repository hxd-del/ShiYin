"""播放会话记忆：把队列、当前曲目、位置、页面和窗口尺寸写进 meta 表。

只持久化不会过期的元数据，在线曲目的短时直链和 raw 对象一律不写入。
恢复时默认只加载本地文件并停在上次位置，不自动出声。
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from PySide6.QtCore import QObject, QTimer

from shiyin.app.core.models import Track

SESSION_META_KEY = "session.v1"
MAX_SESSION_TRACKS = 1000


class SessionService(QObject):
    def __init__(self, repository, playback, settings, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.playback = playback
        self.settings = settings
        self._window = None
        self._page_key = "favorites"
        self._position_ms = 0
        self._last_position_at = 0.0
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(300)
        self._save_timer.timeout.connect(self.flush)
        self._loading = False
        # 默认允许保存：即使 restore() 因任何原因没有执行，用户第一次播放也能落盘。
        self._ready = True
        self._has_activity = False
        self._write_count = 0
        logging.getLogger("shiyin").info("会话服务已创建")

        self.playback.queueChanged.connect(self._on_queue_changed)
        self.playback.currentChanged.connect(self._on_current_changed)
        self.playback.stateChanged.connect(self._schedule)
        try:
            self.playback.backend.positionChanged.connect(self._on_position)
        except Exception:
            pass

    # ---------------- 对外接口 ----------------
    def bind_window(self, window) -> None:
        self._window = window

    def note_page(self, page_key: str) -> None:
        if not page_key or page_key == "search":
            return
        self._page_key = page_key
        self._schedule()

    def restore(self) -> bool:
        """从 meta 恢复队列和页面；返回是否真的恢复了内容。"""
        if not bool(self.settings.get("startup_restore_enabled", True)):
            self._ready = True
            logging.getLogger("shiyin").info("会话恢复：设置已关闭")
            return False
        data = self._load()
        if not data:
            # 老版本没有 session.v1；升级后第一次启动用「最近播放」兜底，
            # 至少把上次听的那首歌放回播放栏，而不是显示空白。
            if self._restore_recent():
                return True
            self._ready = True
            logging.getLogger("shiyin").info("会话恢复：没有历史记录")
            return False
        raw_queue = data.get("queue") or []
        if not isinstance(raw_queue, list) or not raw_queue:
            self._ready = True
            logging.getLogger("shiyin").info("会话恢复：历史队列为空")
            return False

        tracks: list[Track] = []
        index = int(data.get("index") or 0)
        for position, item in enumerate(raw_queue[:MAX_SESSION_TRACKS]):
            if not isinstance(item, dict):
                continue
            track = Track.from_dict(item)
            # 本地文件已经删除时不恢复这一条，避免启动后点播放没有反应。
            if track.is_local and (not track.path or not Path(track.path).exists()):
                if position < index:
                    index -= 1
                continue
            tracks.append(track)
        if not tracks:
            logging.getLogger("shiyin").warning("会话恢复失败：队列里的本地文件都不存在")
            self._ready = True
            return False

        index = max(0, min(index, len(tracks) - 1))
        position_ms = max(0, int(data.get("position_ms") or 0))
        page = str(data.get("page") or "favorites")
        window_state = data.get("window") if isinstance(data.get("window"), dict) else {}

        self._loading = True
        try:
            self.playback.restore_state(
                tracks, index, position_ms,
                autoplay=bool(self.settings.get("resume_autoplay", False)),
            )
            self._position_ms = position_ms
            self._has_activity = True
            if self._window is not None:
                self._apply_window(window_state)
                page_index = getattr(self._window, "_nav_pages", {}).get(page)
                if page_index is not None:
                    self._window._show_page(page_index, push=False)
                self._page_key = page
                player_bar = getattr(self._window, "player_bar", None)
                if player_bar is not None:
                    player_bar.show_restored(self.playback.current, position_ms)
        finally:
            self._loading = False
            self._ready = True
        logging.getLogger("shiyin").info(
            "已恢复会话：队列 %d 首，当前第 %d 首，位置 %.1fs，页面 %s",
            len(tracks), index + 1, position_ms / 1000.0, page,
        )
        return True

    def flush(self) -> None:
        """立即落盘，供关窗/退出前调用。"""
        self._save_timer.stop()
        if self._loading:
            return
        self._write()

    def _restore_recent(self) -> bool:
        """没有 session.v1 时（例如刚从旧版升级）用最近播放兜底。"""
        try:
            recent = self.repository.playlist_tracks("recent")
        except Exception as err:
            logging.getLogger("shiyin").warning("读取最近播放失败：%s", err)
            return False
        tracks = [
            track for track in recent
            if not (track.is_local and (not track.path or not Path(track.path).exists()))
        ]
        if not tracks:
            return False
        track = tracks[0]
        self._loading = True
        try:
            self.playback.restore_state([track], 0, 0, autoplay=False)
            self._position_ms = 0
            self._has_activity = True
            player_bar = getattr(self._window, "player_bar", None) if self._window else None
            if player_bar is not None:
                player_bar.show_restored(track, 0)
        finally:
            self._loading = False
            self._ready = True
        logging.getLogger("shiyin").info("会话恢复：无 session.v1，已用最近播放兜底：%s", track.title)
        return True

    # ---------------- 信号 ----------------
    def _on_queue_changed(self) -> None:
        if self.playback.queue:
            self._has_activity = True
        self._schedule()

    def _on_current_changed(self, track) -> None:
        if track is not None:
            self._has_activity = True
            self._position_ms = 0
        self._schedule()
        # 切歌/首次播放立即落盘，不等 300ms 防抖；避免用户很快关窗时丢掉当前曲目。
        if not self._loading and track is not None:
            self.flush()

    def _on_position(self, position: int) -> None:
        self._position_ms = max(0, int(position))
        now = time.monotonic()
        if now - self._last_position_at >= 1.0:
            self._last_position_at = now
            self._schedule()

    def _schedule(self) -> None:
        if self._loading or not self._ready:
            return
        self._save_timer.start()

    # ---------------- 读写 ----------------
    def _load(self) -> dict:
        raw = self.repository.get_meta(SESSION_META_KEY)
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            logging.getLogger("shiyin").warning("会话记录不是合法 JSON，已忽略")
            return {}
        return data if isinstance(data, dict) else {}

    def _write(self) -> None:
        if not self._ready:
            return
        queue = self.playback.queue
        # 没有播放过、也没有队列时不要写空记录，避免把上次的会话覆盖掉。
        if not queue and not self._has_activity:
            return
        items = [self._serialize_track(track) for track in queue[:MAX_SESSION_TRACKS]]
        index = self.playback.index
        if index >= len(items):
            index = len(items) - 1
        window_state = {}
        if self._window is not None:
            window_state = {
                "w": int(self._window.width()), "h": int(self._window.height()),
            }
        data = {
            "version": 1,
            "queue": items,
            "index": max(0, index),
            "position_ms": max(0, int(self._position_ms)),
            "page": self._page_key,
            "window": window_state,
            "saved_at": int(time.time()),
        }
        try:
            self.repository.set_meta(SESSION_META_KEY, json.dumps(data, ensure_ascii=False))
            if self._write_count == 0:
                logging.getLogger("shiyin").info(
                    "会话已写入：队列 %d 首，当前位置 %.1fs，页面 %s",
                    len(items), data["position_ms"] / 1000.0, data["page"],
                )
            self._write_count += 1
        except Exception as err:
            logging.getLogger("shiyin").warning("会话写入失败：%s", err)

    @staticmethod
    def _serialize_track(track: Track) -> dict:
        """只存恢复所需字段；url/raw/lyric 不落盘，避免过期和膨胀。"""
        data = {
            "title": track.title,
            "artist": track.artist,
            "album": track.album,
            "source": track.source,
            "source_id": track.source_id,
            "duration_ms": int(track.duration_ms or 0),
            "ext": track.ext,
            "bitrate": int(track.bitrate or 0),
            "path": track.path,
            "cover_url": track.cover_url,
        }
        if track.track_id:
            data["track_id"] = track.track_id
        return data

    def _apply_window(self, state: dict) -> None:
        try:
            width = max(960, int(state.get("w") or 1180))
            height = max(640, int(state.get("h") or 760))
            self._window.resize(width, height)
        except (TypeError, ValueError, AttributeError):
            pass
